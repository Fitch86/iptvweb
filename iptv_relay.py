#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
iptv_relay.py — 浙江电信 IPTV RTSP 单播/回看 → MPEG-TS 中继 (纯stdlib)
原理: RTSP(302跟随) → SETUP TCP交错 → PLAY → 剥RTP头 → TS重对齐 → 输出
已验证: 华为HMS_V1R2平台, m=video MP2T/AVP 33, ~8Mbps, 回看含IDR关键帧

用法(路由器上):
  守护模式(推荐):  python3 /usr/bin/iptv_relay.py --daemon 0.0.0.0 4023
      播放地址: http://<路由器>:4023/stream?url=<urlencode的rtsp>&seek=<YYYYMMDDHHMMSS-YYYYMMDDHHMMSS>
      seek 省略=单播直播
  单发模式:        python3 iptv_relay.py <rtsp_url> [playseek] > out.ts
"""
import sys, socket, re, time, threading
from urllib.parse import urlparse, parse_qs, quote
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

UA = "iptv_relay/1.0"
CSEQ = 0

def hostport(u):
    m = re.match(r"rtsp://([^/:]+)(?::(\d+))?", u)
    if not m: raise ValueError("bad rtsp url: " + u)
    return m.group(1), int(m.group(2) or 554)

def _tcp_connect(h, p, timeout=15):
    """直连(数字IP不走getaddrinfo, 绕开python3-light缺idna编码的问题)"""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    s.connect((h, p))
    return s

def rtsp_connect(url, seek=None, log=lambda *a: None):
    """DESCRIBE(跟随302) -> 返回 (sock, session, final_url)"""
    global CSEQ
    full = url + (("?playseek=" + seek) if seek else "")
    s = None
    for hop in range(6):
        h, p = hostport(full)
        s = _tcp_connect(h, p)
        CSEQ += 1
        s.sendall((f"DESCRIBE {full} RTSP/1.0\r\nCSeq: {CSEQ}\r\nUser-Agent: {UA}\r\n"
                   f"Accept: application/sdp\r\n\r\n").encode())
        t, _ = _read_resp(s)
        status = t.splitlines()[0] if t else ""
        loc = re.search(r"Location:\s*(\S+)", t, re.I)
        if status.startswith("RTSP/1.0 3") and loc:
            log(f"302 -> {loc.group(1)[:80]}...")
            full = loc.group(1); s.close(); s = None; continue
        if not status.startswith("RTSP/1.0 2"):
            s.close()
            raise RuntimeError("DESCRIBE失败: " + status)
        break
    sess = re.search(r"Session:\s*([^;\r\n]+)", t, re.I)
    sess = sess.group(1) if sess else ""
    return s, sess, full

def _read_resp(s):
    buf = b""
    while b"\r\n\r\n" not in buf:
        d = s.recv(4096)
        if not d: break
        buf += d
    head, _, rest = buf.partition(b"\r\n\r\n")
    text = head.decode(errors="replace")
    m = re.search(r"Content-Length:\s*(\d+)", text, re.I)
    body = rest
    if m:
        need = int(m.group(1)) - len(rest)
        while need > 0:
            d = s.recv(65536)
            if not d: break
            body += d; need -= len(d)
    return text, body

def pump(s, sess, final_url, write, stop_ev, log=lambda *a: None, idle_timeout=25):
    """SETUP(交错0-1) -> PLAY -> 剥RTP -> TS重对齐 -> write(bytes)"""
    global CSEQ
    CSEQ += 1
    s.sendall((f"SETUP {final_url} RTSP/1.0\r\nCSeq: {CSEQ}\r\nUser-Agent: {UA}\r\n"
               f"Transport: RTP/AVP/TCP;interleaved=0-1\r\nSession: {sess}\r\n\r\n").encode())
    t, _ = _read_resp(s)
    if not t.startswith("RTSP/1.0 2"):
        raise RuntimeError("SETUP失败: " + t.splitlines()[0])
    ch = 0
    tr = re.search(r"interleaved=(\d+)-(\d+)", t)
    if tr: ch = int(tr.group(1))
    CSEQ += 1
    s.sendall((f"PLAY {final_url} RTSP/1.0\r\nCSeq: {CSEQ}\r\nUser-Agent: {UA}\r\n"
               f"Session: {sess}\r\n\r\n").encode())
    t, _ = _read_resp(s)
    if not t.startswith("RTSP/1.0 2"):
        raise RuntimeError("PLAY失败: " + t.splitlines()[0])
    log("媒体流已建立 (channel=%d)" % ch)
    carry = b""; total = 0; last = time.time()
    s.settimeout(idle_timeout)
    while not (stop_ev and stop_ev.is_set()):
        try:
            d = s.recv(65536)
        except socket.timeout:
            log("空闲超时, 结束"); break
        if not d: break
        last = time.time()
        buf = carry + d; i = 0; out = bytearray()
        while i + 4 <= len(buf):
            if buf[i] == 0x24:  # '$' 交错帧
                c = buf[i + 1]; ln = int.from_bytes(buf[i + 2:i + 4], "big")
                if i + 4 + ln > len(buf): break
                if c == ch:
                    pl = buf[i + 4:i + 4 + ln]
                    if len(pl) >= 12: out += pl[12:]
                i += 4 + ln
            else:
                i += 1
        carry = buf[i:]
        if out:
            ts = _realign(bytes(out))
            if ts: write(ts); total += len(ts)
    try:
        CSEQ += 1
        s.sendall((f"TEARDOWN {final_url} RTSP/1.0\r\nCSeq: {CSEQ}\r\nUser-Agent: {UA}\r\n"
                   f"Session: {sess}\r\n\r\n").encode())
    except Exception: pass
    s.close()
    log(f"会话结束, 共输出 {total} 字节 TS")

_TSSTATE = threading.local()
def _realign(data):
    """按188字节对齐TS(找0x47并校验下一包)"""
    prev = getattr(_TSSTATE, "carry", b"")
    data = prev + data
    out = bytearray(); i = 0
    n = len(data)
    while i + 188 <= n:
        if data[i] == 0x47:
            if i + 376 <= n and data[i + 188] != 0x47:
                i += 1; continue
            out += data[i:i + 188]; i += 188
        else:
            i += 1
    _TSSTATE.carry = data[i:]
    return bytes(out)

# ---------- 守护模式 ----------
class QuietHTTPServer(ThreadingHTTPServer):
    """绕过 HTTPServer.server_bind 里的 getfqdn()(OpenWrt python3-light 缺 idna 编码)"""
    def server_bind(self):
        import socketserver
        socketserver.TCPServer.server_bind(self)
        host, port = self.server_address[:2]
        self.server_name = host
        self.server_port = port

class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    def log_message(self, *a): pass

    def _cors(self):
        """跨域头: 页面在 :80/:443, 中继在 :4023, 属跨源"""
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Max-Age", "86400")

    def do_OPTIONS(self):
        # 预检请求: 204 + CORS头, 无body
        self.send_response(204)
        self._cors()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        if self.path.startswith("/status"):
            body = b"iptv_relay ok\n"; self.send_response(200)
            self._cors()
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(body))); self.end_headers()
            self.wfile.write(body); return
        if not self.path.startswith("/stream"):
            self.send_error(404); return
        q = parse_qs(urlparse(self.path).query)
        url = (q.get("url") or [""])[0]
        seek = (q.get("seek") or [None])[0]
        if not url.startswith("rtsp://"):
            self.send_error(400, "need url"); return
        self.send_response(200)
        self._cors()
        self.send_header("Content-Type", "video/mp2t")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()
        stop = threading.Event()
        def write_raw(b):
            self.wfile.write(b)
            self.wfile.flush()
        try:
            self.wfile.flush()  # 立即把响应头推给客户端
            s, sess, final = rtsp_connect(url, seek, log=lambda *a: print(*a, flush=True))
            pump(s, sess, final, write_raw, stop,
                 log=lambda *a: print(*a, flush=True))
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as e:
            print("stream错误:", e, flush=True)
        # Connection: close 收尾, 无需结束块
        try:
            self.wfile.flush()
        except Exception:
            pass

def main():
    if len(sys.argv) >= 2 and sys.argv[1] == "--daemon":
        ip = sys.argv[2] if len(sys.argv) > 2 else "0.0.0.0"
        port = int(sys.argv[3]) if len(sys.argv) > 3 else 4023
        print(f"iptv_relay daemon on {ip}:{port}  /stream?url=<rtsp>&seek=<B-E>", flush=True)
        QuietHTTPServer((ip, port), Handler).serve_forever()
        return
    url = sys.argv[1]
    seek = sys.argv[2] if len(sys.argv) > 2 else None
    s, sess, final = rtsp_connect(url, seek, log=lambda *a: print(*a, file=sys.stderr, flush=True))
    pump(s, sess, final, lambda b: (sys.stdout.buffer.write(b), sys.stdout.buffer.flush()),
         None, log=lambda *a: print(*a, file=sys.stderr, flush=True))

if __name__ == "__main__":
    main()

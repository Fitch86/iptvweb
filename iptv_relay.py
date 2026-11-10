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
_REQ_LOCK = threading.Lock()
_REQ_SEQ = 0

def _new_request_id():
    global _REQ_SEQ
    with _REQ_LOCK:
        _REQ_SEQ += 1
        return "%s-%04d" % (time.strftime("%H%M%S"), _REQ_SEQ)

def _safe_rtsp_target(u):
    """只返回不含查询参数/凭据的目标信息，避免日志泄露 URL token。"""
    try:
        p = urlparse(u)
        return "%s://%s%s" % (p.scheme, p.hostname or "?", p.path or "/")
    except Exception:
        return "<invalid-rtsp-url>"

def _read_resp_diag(s, reqid, phase, log):
    started = time.monotonic()
    log("[%s] %s response_wait begin" % (reqid, phase))
    try:
        result = _read_resp(s)
    except Exception as e:
        log("[%s] %s response_wait ERROR after %.3fs: %s" %
            (reqid, phase, time.monotonic() - started, e))
        raise
    head, body = result
    status = head.splitlines()[0] if head else "<empty>"
    log("[%s] %s response_wait done %.3fs status=%s body_bytes=%d" %
        (reqid, phase, time.monotonic() - started, status, len(body)))
    return result

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

def rtsp_connect(url, seek=None, log=lambda *a: None, reqid="-"):
    """DESCRIBE(跟随302) -> 返回 (sock, session, final_url)"""
    global CSEQ
    full = url + (("?playseek=" + seek) if seek else "")
    s = None
    for hop in range(6):
        h, p = hostport(full)
        target = _safe_rtsp_target(full)
        log("[%s] DESCRIBE hop=%d/6 target=%s seek_present=%s" %
            (reqid, hop + 1, target, "yes" if "playseek=" in full else "no"))
        started = time.monotonic()
        try:
            s = _tcp_connect(h, p)
        except Exception as e:
            log("[%s] TCP_CONNECT ERROR target=%s after %.3fs: %s" %
                (reqid, target, time.monotonic() - started, e))
            raise
        log("[%s] TCP_CONNECT OK target=%s elapsed=%.3fs" %
            (reqid, target, time.monotonic() - started))
        CSEQ += 1
        s.sendall((f"DESCRIBE {full} RTSP/1.0\r\nCSeq: {CSEQ}\r\nUser-Agent: {UA}\r\n"
                   f"Accept: application/sdp\r\n\r\n").encode())
        t, _ = _read_resp_diag(s, reqid, "DESCRIBE", log)
        status = t.splitlines()[0] if t else ""
        loc = re.search(r"Location:\s*(\S+)", t, re.I)
        if status.startswith("RTSP/1.0 3") and loc:
            next_url = loc.group(1)
            log("[%s] REDIRECT status=%s location=%s location_has_playseek=%s" %
                (reqid, status, _safe_rtsp_target(next_url),
                 "yes" if "playseek=" in next_url else "no"))
            full = next_url; s.close(); s = None; continue
        if not status.startswith("RTSP/1.0 2"):
            s.close()
            raise RuntimeError("DESCRIBE失败: " + status)
        break
    sess = re.search(r"Session:\s*([^;\r\n]+)", t, re.I)
    sess = sess.group(1) if sess else ""
    log("[%s] DESCRIBE complete session_present=%s final_target=%s" %
        (reqid, "yes" if sess else "no", _safe_rtsp_target(full)))
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

def pump(s, sess, final_url, write, stop_ev, log=lambda *a: None, idle_timeout=25, reqid="-"):
    """SETUP(交错0-1) -> PLAY -> 剥RTP -> TS重对齐 -> write(bytes)"""
    global CSEQ
    log("[%s] SETUP begin target=%s session_present=%s" %
        (reqid, _safe_rtsp_target(final_url), "yes" if sess else "no"))
    CSEQ += 1
    s.sendall((f"SETUP {final_url} RTSP/1.0\r\nCSeq: {CSEQ}\r\nUser-Agent: {UA}\r\n"
               f"Transport: RTP/AVP/TCP;interleaved=0-1\r\nSession: {sess}\r\n\r\n").encode())
    t, _ = _read_resp_diag(s, reqid, "SETUP", log)
    if not t.startswith("RTSP/1.0 2"):
        raise RuntimeError("SETUP失败: " + (t.splitlines()[0] if t else "<empty>"))
    ch = 0
    tr = re.search(r"interleaved=(\d+)-(\d+)", t)
    if tr: ch = int(tr.group(1))
    log("[%s] SETUP complete interleaved_channel=%d" % (reqid, ch))
    log("[%s] PLAY begin target=%s" % (reqid, _safe_rtsp_target(final_url)))
    CSEQ += 1
    s.sendall((f"PLAY {final_url} RTSP/1.0\r\nCSeq: {CSEQ}\r\nUser-Agent: {UA}\r\n"
               f"Session: {sess}\r\n\r\n").encode())
    t, _ = _read_resp_diag(s, reqid, "PLAY", log)
    if not t.startswith("RTSP/1.0 2"):
        raise RuntimeError("PLAY失败: " + (t.splitlines()[0] if t else "<empty>"))
    log("[%s] PLAY accepted (channel=%d); waiting for RTP data" % (reqid, ch))
    carry = b""; total = 0; last = time.time()
    media_started = last; last_report = last
    recv_bytes = 0; interleaved_frames = 0
    rtp_frames = 0; rtp_payload_bytes = 0; ts_bytes = 0
    s.settimeout(idle_timeout)
    while not (stop_ev and stop_ev.is_set()):
        try:
            d = s.recv(65536)
        except socket.timeout:
            log("[%s] MEDIA_IDLE_TIMEOUT elapsed=%.1fs since_last_data=%.1fs recv_tcp=%d interleaved=%d rtp_frames=%d rtp_payload=%d ts_out=%d" %
                (reqid, time.time() - media_started, time.time() - last,
                 recv_bytes, interleaved_frames, rtp_frames, rtp_payload_bytes, total))
            break
        if not d:
            log("[%s] upstream TCP EOF" % reqid)
            break
        last = time.time()
        recv_bytes += len(d)
        buf = carry + d; i = 0; out = bytearray()
        while i + 4 <= len(buf):
            if buf[i] == 0x24:  # '$' 交错帧
                c = buf[i + 1]; ln = int.from_bytes(buf[i + 2:i + 4], "big")
                if i + 4 + ln > len(buf): break
                interleaved_frames += 1
                if c == ch:
                    pl = buf[i + 4:i + 4 + ln]
                    if len(pl) >= 12:
                        rtp_frames += 1
                        rtp_payload_bytes += len(pl) - 12
                        out += pl[12:]
                i += 4 + ln
            else:
                i += 1
        carry = buf[i:]
        if out:
            ts = _realign(bytes(out))
            if ts:
                try:
                    write(ts)
                except Exception as e:
                    log("[%s] HTTP_CLIENT_WRITE ERROR after %.3fs: %s" %
                        (reqid, time.time() - last, e))
                    raise
                total += len(ts); ts_bytes += len(ts)
        now = time.time()
        if now - last_report >= 5:
            log("[%s] MEDIA stats elapsed=%.1fs recv_tcp=%d interleaved=%d rtp_frames=%d rtp_payload=%d ts_out=%d since_last_data=%.1fs" %
                (reqid, now - media_started,
                 recv_bytes, interleaved_frames, rtp_frames, rtp_payload_bytes,
                 ts_bytes, now - last))
            last_report = now
    try:
        CSEQ += 1
        s.sendall((f"TEARDOWN {final_url} RTSP/1.0\r\nCSeq: {CSEQ}\r\nUser-Agent: {UA}\r\n"
                   f"Session: {sess}\r\n\r\n").encode())
    except Exception: pass
    s.close()
    log("[%s] SESSION_END recv_tcp=%d interleaved=%d rtp_frames=%d rtp_payload=%d ts_out=%d" %
        (reqid, recv_bytes, interleaved_frames, rtp_frames, rtp_payload_bytes, total))

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
        reqid = _new_request_id()
        log = lambda *a: print(*a, flush=True)
        log("[%s] HTTP_GET begin seek_present=%s target=%s" %
            (reqid, "yes" if seek else "no", _safe_rtsp_target(url)))
        phase = "RTSP_CONNECT"
        stop = threading.Event()
        def write_raw(b):
            self.wfile.write(b)
            self.wfile.flush()
        try:
            self.wfile.flush()  # 立即把响应头推给客户端
            s, sess, final = rtsp_connect(url, seek, log=log, reqid=reqid)
            phase = "PUMP_SETUP_PLAY_MEDIA"
            pump(s, sess, final, write_raw, stop, log=log, reqid=reqid)
            log("[%s] HTTP_GET complete" % reqid)
        except (BrokenPipeError, ConnectionResetError) as e:
            log("[%s] HTTP_CLIENT_DISCONNECTED phase=%s error=%s" % (reqid, phase, e))
        except Exception as e:
            log("[%s] STREAM_ERROR phase=%s type=%s error=%s" %
                (reqid, phase, type(e).__name__, e))
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

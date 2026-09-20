# luci-app-iptvweb 0.2.2-rev4.4

OpenWrt LuCI IPTV Web Player。rev4.4 先修复 rev4.2 装完频道列表空白的阻塞问题，再继续做 Windows Chromium 上 CCTV1 那次稳定的 1～2 秒初始化 waiting 对照实验。

## rev4.2 频道列表故障

rev4.2 的诊断 IIFE 在定义 `stop` 之前调用了 `reset()`：

```js
R.reset = function () { R.stop(); /* ... */ };
R.reset();          // TypeError: R.stop is not a function
R.stop = function () { /* ... */ };
```

这是运行时异常，不是语法错误。异常会中断整页脚本，`load()` 根本不会执行，所以侧栏频道为空、状态栏也不提示 M3U 失败。本地已用同样脚本复现：`TypeError: R.stop is not a function`。

顺带两个会污染测试的问题一并去掉：

- `play()` 里调用了未定义的 `startRawTsProbe()`，即便频道列表修好也会在点播时再崩一次。
- 播放时自动再 `fetch` 同一条 `/cgi-bin/iptvweb-stream` 做 TS 探针，等于第二个 udpxy 客户端。rev4.4 只在你点「浏览器 TS 分析」或「路由器抓包」且先停止播放后才抓 TS。

另外，rev4.2 的 `install.sh` 每次都会覆盖 `/etc/config/iptvweb`。如果 LuCI 里填过自定义 M3U，装完会被还原成默认 `myepg.org`。rev4.4 不再覆盖已有配置。

装完请 **Ctrl+F5** 强制刷新 `http://192.168.1.1/iptv/`。

## 初始化 waiting 的判断（不是“还不能播”）

CCTV1：MPEG-TS / H.264 High@4.1 1080p25 / MP3 48 kHz stereo。  
Windows 10 Chrome/Edge 153：首帧约 1.9s，随后稳定两次 waiting，再连续流畅。Firefox、Android、Win11 Chrome、VLC 正常。4K HEVC 在同一套 Chromium 上立即连续播放。`buffered` 可以已经是几十秒、`readyState=4`，仍然 waiting。

### 1. 最可能发生在哪一层

| 层 | 可能性 | 理由 |
| --- | --- | --- |
| HTTP / udpxy | 低 | 组播和 VLC 正常；waiting 时 buffer 已经很大 |
| MPEG-TS 本身 | 中（要验证 PTS/GOP） | 可能有 A/V 起始 PTS 差或 RAI/GOP≈1–2s，但 Firefox 吃同一条流不卡 |
| mpegts.js demux | 中 | `isLive=false` 把 duration 显示成当前 buffered 长度；`fixAudioTimestampGap` 默认是 true，当前实验基线却关掉了 |
| MSE SourceBuffer | 高 | `video.buffered` 是音视频 track 的交集；Chrome 对 MP3-in-fMP4 / timestampOffset 更挑剔 |
| Chromium media pipeline / A/V sync | **最高** | 典型：已有编码数据，但下一个可同步的 A/V 帧对还没就绪 |
| H.264 decoder | 低-中 | 已经有 firstFrame；refFrames=1，基本不是 B 帧重排 |
| MP3 decoder | **高** | 只有 H.264+MP3 的普通频道中招；4K（往往不是 MP3）立刻播 |
| 纯网络抖动 | 排除 | 每次重选 CCTV1 行为几乎相同 |

结论：这是 **Windows Chromium + MSE + H.264/MP3 初始化路径**，不是 IPTV 网络。HTML5 的 `waiting` 不等于“没有字节”。Chrome 在下面情况也会 waiting：

- 音视频 SourceBuffer 在 `currentTime` 处还对不齐
- MP3 解码器 / audio renderer 还在 preroll
- coded frame processing 暂时不产出可渲染帧
- 解码队列空了，即使 MSE 里已经有几十秒 fMP4

所以 `buffered=0–58s`、`readyState=4` 仍然 waiting 完全说得通：缺的是 **可播放的解码帧对**，不是 TS 字节。

mpegts.js 文档里 `fixAudioTimestampGap` **默认 true**（用静音帧填音频时间戳空洞）。当前基线显式设成 `false`。这是下一步最值得做的单变量，但不要和 video-only 同时改。

### 2. 下一组最小变量实验（一次只改一项）

基线保持：

```
isLive:false
enableWorker:true
enableWorkerForMSE:false
enableStashBuffer:true
stashInitialSize:384*1024
lazyLoad:true
fixAudioTimestampGap:false
```

不要改硬件加速、不要改回 `isLive=true`、不要动 CDN / Worker URL。

按这个顺序测 CCTV1，每次只改一项，复制日志：

1. **A/V 正常**（基线）。看 `WAITING_SNAPSHOT`：若 `ahead>=1s` 且 `readyState>=3`，日志会明确写“不是缺数据”。
2. **Video-only (`hasAudio=false`)**。若 waiting 消失 → 音频轨 / A-V sync / MP3。若还在 → GOP/H.264/MSE 视频轨。
3. **保留音轨但静音**（`hasAudio` 仍 true，`video.muted=true`）。若 video-only 好、静音仍卡 → 问题在 demux/MSE 音频路径，不是扬声器。
4. 回到 A/V，只勾选 **fixAudioTimestampGap**。
5. 再单独试 **waiting 时微移 currentTime**（Chrome MSE 已知 unblock 手法，默认关）。
6. 停止播放后点 **浏览器 TS 分析(12s)**，看 `A-V start delta` 和 RAI 间隔。
7. 需要 ffprobe 时再点 **路由器抓包 15s**，然后从电脑 scp。

对照时请看日志里的：

- `WAITING_SNAPSHOT` / `WAITING_WITH_BUFFER`
- `decV` / `decA`（Chrome `webkit*DecodedByteCount`）
- `mse=` 里 audio/video SourceBuffer 各自的 `buffered` 和 `timestampOffset`

若 waiting 时 `decV` 在涨、`decA` 不动 → MP3 解码器没在吐帧。  
若两个 SourceBuffer 的 buffered 起点差 1～2 秒 → Chrome 在等交集。

### 3. 在 OpenWrt 上抓原始 TS

先 **停止网页播放**，避免第二个 udpxy 客户端。

播放器按钮「路由器抓包 15s」会写 `/tmp/iptvweb-capture.ts`。或手动：

```sh
# 先停掉网页播放。CCTV1 组播按你的实际地址改。
killall uclient-fetch 2>/dev/null || true
uclient-fetch -O /tmp/iptvweb-capture.ts 'http://127.0.0.1:4022/udp/233.50.201.118:5140' &
PID=$!
sleep 15
kill $PID
ls -l /tmp/iptvweb-capture.ts
```

电脑上：

```sh
scp root@192.168.1.1:/tmp/iptvweb-capture.ts .

ffprobe -hide_banner \
  -show_entries stream=index,codec_name,codec_type,profile,level,width,height,r_frame_rate,start_time,start_pts,sample_rate,channels \
  -of json iptvweb-capture.ts

# GOP / IDR：看 pict_type=I 的间隔（秒）
ffprobe -v error -select_streams v:0 \
  -show_entries frame=pict_type,key_frame,pkt_pts_time,pkt_dts_time \
  -of csv=p=0 -read_intervals %+12 iptvweb-capture.ts

# 音频包时间戳
ffprobe -v error -select_streams a:0 \
  -show_entries packet=pts_time,dts_time,duration_time,size \
  -of csv=p=0 -read_intervals %+5 iptvweb-capture.ts
```

若已装 tsduck：

```sh
tsanalyze iptvweb-capture.ts
tsp -I file iptvweb-capture.ts -P continuity -P pcrbitrate -O drop
```

关注：第一个视频 PTS、第一个音频 PTS、两者差值、第一个 IDR 距 PAT/PMT 多远、GOP 是否约 1～2 秒、是否有 PCR/CC discontinuity。

## 安装

```sh
sh install.sh
```

然后强制刷新 `http://192.168.1.1/iptv/`。M3U 仍在 LuCI → Services → IPTV Web。

# luci-app-iptvweb 0.2.2-rev4.25

## rev4.25

修复 Safari MP2PCM 音频"连续但变慢、音调变低"的根因：mpg123 解码输出的 PCM 采样率（如 48 kHz）一直被忽略，AudioWorklet 与 ScriptProcessor 两个后端都按 AudioContext 自身时钟 1:1 消费。当设备 AudioContext 默认采样率是 44.1 kHz 时，48 kHz PCM 以 44100/48000 ≈ 0.919 倍速播放——音调变低、语速变慢，并每秒落后视频约 0.08 s。rev4.25 在主线程做线性插值重采样（跨 chunk 相位保持，无累计漂移）到 ctx.sampleRate；两个后端同时生效。新增验证日志：AudioContext rate、first chunk decoded/ctx/resample。诊断面板【独立音频】新增 backend / ctx / resample 字段，并移除音频回调里的逐次 updateDiag（面板刷新交给 500ms diagTimer）。

rev4.17 以 rev4.14/4.16.3 的 Safari H.264 Video-only 路径为基线。视频链不变；新增 MPEG Audio PES 提取实验：路由器从 IPTV MPEG-TS 中定位 PMT 的 MPEG Audio PID，提取完整 MPEG Audio 帧到 `iptvweb-audio-pes`，浏览器 Safari 侧使用 WebAudio `AudioContext.decodeAudioData()` 尝试解码。

rev4.17.2 仅修正音频 CGI 在 OpenWrt Lua 5.1 环境下使用 Lua 5.3 位运算语法导致的 HTTP 500；改用兼容 Lua 5.1 的算术位操作。

本版本不再使用 rev4.16.3 的独立原生 `<audio>` 播放路径。WebAudio 音频实验失败不会影响 Video-only 视频播放。


## rev4.17.4

仅修复 Lua 运行时依赖：OpenWrt 25.12 的音频 CGI 使用 Lua 5.1，对应 APK 包名为 `lua`。Makefile 增加 `+lua` 依赖；直接运行 `install.sh` 时若系统没有 `lua`，会自动执行 `apk add lua`。Safari H.264 Video-only 播放链、MPEG Audio 提取算法和 WebAudio 实验均未修改。


## rev4.18

很小的 MP2 能力验证版：独立音频 CGI 只返回有限数量的完整 MPEG-1 Layer II 帧（约 64 KiB），避免无限流导致 fetch 永远等待；Safari WebAudio 对这段有限 MP2 数据调用 `AudioContext.decodeAudioData()`。视频 H.264 Video-only / Safari MSE fallback 链完全不变。

## rev4.20
Safari audio experiment based on rev4.18.2. The router still extracts a finite MPEG Audio/MP2 sample. The browser no longer calls `decodeAudioData()` for MP2; it loads a local `mpg123-decoder` 1.0.3 WASM bundle, decodes MPEG Layer I/II/III to Float32 PCM, creates an AudioBuffer, and plays it through WebAudio. The decoder bundle is downloaded during installation and served locally; there is no runtime CDN dependency.

## rev4.21.1

在 rev4.20 的 Safari H.264 Video-only + TS filter 基础上，改为连续 MP2PCM：

- `iptvweb-audio-pes` 持续从 udpxy IPTV MPEG-TS 中提取完整 MPEG Audio 帧，不再只返回一次性短音频块。
- 浏览器使用本地 `mpg123-decoder 1.0.3` 增量解码 MPEG Layer I/II/III。
- PCM 通过 WebAudio `AudioBufferSourceNode` 连续排程，保持小延迟队列，避免“一开始有声、音频块播完就没声”。
- 视频首帧后建立音频锚点；持续估算 A/V 漂移，漂移过大时丢弃已排程音频并重新建立短延迟锚点，避免实时直播延迟无限累积。
- Safari 视频 TS filter / MSE fallback 不改。

当前 CCTV1 实际音频已确认是 MPEG-1 Layer II，224 kbps，44.1 kHz，2 声道。rev4.21.1 的目标是验证连续 MP2PCM 在 Safari 上能否长期稳定播放并保持可接受的 A/V 同步。

### 第三方库

源码包中的 `mpegts.min.js` 和 `mpg123-decoder.min.js` 是安装引导标记；根目录 `install.sh` 会在路由器上下载并安装实际本地 JS/WASM 文件。需要路由器安装时能够访问 jsDelivr 或 unpkg；浏览器运行时不需要访问 CDN。


## rev4.23.1

Safari MP2PCM 优先 AudioWorklet + 实时 PCM RingBuffer；在普通 HTTP LAN 页面上 AudioWorklet 不可用时自动使用 ScriptProcessor 实时 PCM RingBuffer 回退。保留 rev4.21.1 的 Safari H.264 Video-only TS filter、连续 `iptvweb-audio-pes` 和本地 `mpg123-decoder 1.0.3`。浏览器不再使用 `AudioBufferSourceNode` 逐块排程，也不再通过 queue cap 丢弃旧 PCM。

- MPEG Layer II 解码结果转换为交错 stereo Float32 PCM。
- AudioWorklet 内部使用约 2 秒 stereo PCM ring buffer，以 AudioContext 时钟连续输出。
- 主线程设置约 1.25 秒的 in-flight backpressure，避免网络/解码突发导致 PCM 无界增长。
- A/V 同步改为比较 Video `currentTime` 与 AudioContext 时钟；普通网络抖动不清空音频，只有较大漂移才重新锚定。
- 诊断增加 ring、inFlight、underrun、overflow。
- 不需要 SharedArrayBuffer/Cross-Origin-Isolation。

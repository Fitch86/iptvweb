# luci-app-iptvweb 0.2.2-rev4.18

rev4.17 以 rev4.14/4.16.3 的 Safari H.264 Video-only 路径为基线。视频链不变；新增 MPEG Audio PES 提取实验：路由器从 IPTV MPEG-TS 中定位 PMT 的 MPEG Audio PID，提取完整 MPEG Audio 帧到 `iptvweb-audio-pes`，浏览器 Safari 侧使用 WebAudio `AudioContext.decodeAudioData()` 尝试解码。

rev4.17.2 仅修正音频 CGI 在 OpenWrt Lua 5.1 环境下使用 Lua 5.3 位运算语法导致的 HTTP 500；改用兼容 Lua 5.1 的算术位操作。

本版本不再使用 rev4.16.3 的独立原生 `<audio>` 播放路径。WebAudio 音频实验失败不会影响 Video-only 视频播放。


## rev4.17.4

仅修复 Lua 运行时依赖：OpenWrt 25.12 的音频 CGI 使用 Lua 5.1，对应 APK 包名为 `lua`。Makefile 增加 `+lua` 依赖；直接运行 `install.sh` 时若系统没有 `lua`，会自动执行 `apk add lua`。Safari H.264 Video-only 播放链、MPEG Audio 提取算法和 WebAudio 实验均未修改。


## rev4.18

很小的 MP2 能力验证版：独立音频 CGI 只返回有限数量的完整 MPEG-1 Layer II 帧（约 64 KiB），避免无限流导致 fetch 永远等待；Safari WebAudio 对这段有限 MP2 数据调用 `AudioContext.decodeAudioData()`。视频 H.264 Video-only / Safari MSE fallback 链完全不变。

## rev4.19
Safari audio experiment based on rev4.18.2. The router still extracts a finite MPEG Audio/MP2 sample. The browser no longer calls `decodeAudioData()` for MP2; it loads a local `mpg123-decoder` 1.0.3 WASM bundle, decodes MPEG Layer I/II/III to Float32 PCM, creates an AudioBuffer, and plays it through WebAudio. The decoder bundle is downloaded during installation and served locally; there is no runtime CDN dependency.

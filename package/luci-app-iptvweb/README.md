# luci-app-iptvweb 0.2.2-rev4.17

rev4.17 以 rev4.14/4.16.3 的 Safari H.264 Video-only 路径为基线。视频链不变；新增 MPEG Audio PES 提取实验：路由器从 IPTV MPEG-TS 中定位 PMT 的 MPEG Audio PID，提取完整 MPEG Audio 帧到 `iptvweb-audio-pes`，浏览器 Safari 侧使用 WebAudio `AudioContext.decodeAudioData()` 尝试解码。

本版本不再使用 rev4.16.3 的独立原生 `<audio>` 播放路径。WebAudio 音频实验失败不会影响 Video-only 视频播放。

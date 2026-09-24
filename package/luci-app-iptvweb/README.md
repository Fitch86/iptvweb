# luci-app-iptvweb 0.2.2-rev4.7

rev4.7 在 rev4.6 PID290 原始 PES 解剖基础上加入：

- E-AC-3 帧头精确解析：`0x0B77`、frame size、fscod/numblkscod、sample rate、acmod、LFE、bsid、channels、samples/frame、bitrate、frame duration。
- Private PES `stream_type=0x06` / `stream_id=0xBD` 的 E-AC-3 连续帧检测。
- 浏览器兼容性实验：`audio/mp4; codecs="ec-3"`、HEVC+E-AC-3 的 `canPlayType()` / `MediaSource.isTypeSupported()`，以及可用时的 WebCodecs `AudioDecoder.isConfigSupported()`。
- TS 分析仍先停止播放器再抓流，避免第二个 udpxy 客户端抢同一组播。
- 修复 rev4.6 分析器中 `len is not defined` 类变量错误：所有长度均从已定义的 PES/frame 字段计算。

注意：mpegts.js 1.8.0 官方版本已加入 MPEG-TS E-AC-3 支持，但本频道的 E-AC-3 是 `stream_type=0x06` + `0xBD` Private PES，因此 rev4.7 先把实际封装和浏览器能力完整测出来；本版不宣称已经完成 Private-PES→MSE 的自动转封装。citeturn1search0turn1search2

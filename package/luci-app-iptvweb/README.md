# luci-app-iptvweb 0.2.2-rev4.11

本版目标：只解决**普通 IPTV 频道的 iOS Safari 播放**，不再继续针对北京卫视4K、内蒙古等特殊编码频道做兼容性优化。

- 基于 rev4.7，保留频道列表、M3U、udpxy、长连接 CGI、诊断功能。
- iOS/iPadOS Safari（iOS 17.1+）识别后走 mpegts.js 的 ManagedMediaSource 路径，并对该路径使用 `isLive=true`。mpegts.js 官方从 v1.8.0 起支持 iOS 17.1+ ManagedMediaSource。
- 其他浏览器保持现有 `isLive=false` 路径，避免改变已经验证的桌面/Android 行为。
- 安装脚本改为优先获取 mpegts.js 1.8.2。
- 北京卫视4K（H.265 + E-AC-3）以及内蒙古等异常频道明确列为非本版目标。

官方 mpegts.js 文档确认：iOS Safari 17.1+ 通过 ManagedMediaSource 支持 MPEG-TS 播放；同时 v1.8.x 已支持 MPEG-TS MP3/AC-3/E-AC-3 等音频解析。


## rev4.11 实验逻辑

- iOS/iPadOS Safari 普通频道初始保持完整 A/V demux。
- 只有 mpegts.js 报告 MSE 错误时，才销毁当前 A/V player，并重新建立一次 `hasAudio=false` 的 Video-only player。
- 每个频道最多自动回退一次；回退后的 Video-only 错误不会再次递归回退。
- 非 iOS Safari 不启用该自动回退。
- 该版本用于验证“Safari A/V MSE 失败是否可通过运行时去掉音轨而恢复视频”。

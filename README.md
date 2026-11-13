# IPTV Web for OpenWrt — RC2.3

轻量级 OpenWrt LuCI IPTV 网页播放器。通过 M3U 频道列表和路由器上的 udpxy 接收组播 MPEG-TS，并在浏览器中播放。

> **版本：RC2.3（包版本 `0.2.2-rc2.3`）**  
> RC2.3 基于 `rc2.2`，新增 4023 中继回看，直播默认优先使用 4022 组播；保留 iOS Safari HEVC/4K 处理、Safari 回看音频同步及播放诊断日志。播放器上方显示诊断入口和状态；节目单工具栏集中放置回看/返回直播、播放直播、停止和刷新操作。

## 功能

- 通过 LuCI 配置 M3U 播放列表 URL、udpxy 地址、缓存文件和缓存有效期。
- 自动读取并解析 M3U，按频道分组展示频道名称和台标。
- 获取并缓存多日 XMLTV 节目单（默认 `https://epg.zsdc.eu.org/t.xml.gz`），按 `tvg-id` 匹配频道；频道列表显示当前节目，选中频道后显示可横向滚动的节目时间轴。
- 支持回看的频道在频道列表中提供“回看”入口；进入频道节目单后，点击已播出节目，再使用节目单工具栏的“回看”按钮。当前节目可回看已播部分，未来节目不可选。
- 支持刷新频道列表、重新初始化当前频道、跳到当前缓冲区的最新位置，以及停止并断开当前流。
- 通过本机 CGI 将 udpxy 的组播 HTTP 流转发给浏览器。
- 桌面浏览器保留 mpegts.js 的常规音视频播放路径。
- iOS/iPadOS Safari 根据探测到的音轨类型选择兼容路径：
  - MPEG-1/2 Audio（PMT stream type `0x03/0x04`）：视频走无音轨 MSE 路径；音频由本地 `mpg123-decoder` 解码为 PCM，再通过 Web Audio 播放。
  - AAC（常见 stream type `0x0F/0x11`）或无法确定音轨类型时，保留常规 A/V MSE 路径，不强制切换到 video-only。
- MP2PCM 根据 AudioContext 的输出采样率进行采样率转换，避免输入与输出采样率不一致时出现音频速度或音调异常。
- 播放器运行时使用路由器本地的 JavaScript 资源，不需要浏览器播放时访问 CDN。
- 安装脚本保留已有的 `/etc/config/iptvweb`，升级时不会覆盖已保存的 M3U 和 udpxy 配置。

## 版本与文件

版本标识统一为：

| 位置 | 版本标识 |
| --- | --- |
| 页面标题与播放器页头 | `RC2.3` |
| 页面内部版本常量 | `RC2.3` |
| OpenWrt 包版本 | `0.2.2-rc2.3` |
| 安装脚本输出 | `0.2.2-rc2.3` |

主要目录：

- `package/luci-app-iptvweb/Makefile`：OpenWrt 软件包定义。
- `package/luci-app-iptvweb/files/www/iptv/index.html`：网页播放器。
- `package/luci-app-iptvweb/files/www/cgi-bin/`：M3U、MPEG-TS 转发和 Safari 音轨探测/音频处理 CGI。
- `package/luci-app-iptvweb/files/www/luci-static/resources/iptvweb/`：播放器依赖的本地 JavaScript 资源及 Web Audio worklet。
- `package/luci-app-iptvweb/files/etc/uci-defaults/99-iptvweb`：首次启动时补齐本地播放资源。
- `install.sh`：在已运行的 OpenWrt 系统上安装或升级文件。

## 环境要求

- OpenWrt / LuCI。
- `uhttpd`、`luci-base` 和 Lua 运行时。
- 已配置并可访问的 udpxy 服务，用于把组播 MPEG-TS 转成 HTTP 流。
- 路由器能在安装或首次启动时获取播放器依赖；如果设备无法访问 CDN，应确保对应的完整依赖文件已放在本地资源目录中。

安装脚本使用 mpegts.js 1.8.2 和 mpg123-decoder 1.0.3。它会优先尝试从 jsDelivr 下载，失败时再尝试 unpkg；若下载失败且路由器上已有有效版本，则保留现有文件。

## 安装或升级

在仓库根目录执行：

```sh
sh install.sh
```

脚本需要以 root 身份运行。它会检查 Lua 运行时、安装网页播放器与 CGI、准备本地依赖，并重启 rpcd/uhttpd。已有的 `/etc/config/iptvweb` 会被保留。

安装完成后访问：

```text
http://192.168.1.1/iptv/
```

在 LuCI 中进入 **Services → IPTV Web**，设置：

- **M3U playlist URL**：频道列表地址。
- **udpxy address**：udpxy 的 `主机或 IP:端口`，例如 `192.168.1.1:4022`。
- **EPG XMLTV URL**：默认 `https://epg.zsdc.eu.org/t.xml.gz`；升级会迁移旧默认地址，同时保留用户自定义地址。
- **EPG cache TTL**：节目单缓存有效期，默认 21600 秒（6 小时）。
- **M3U cache TTL / cache file**：频道列表缓存设置。

如果升级后仍看到旧页面，请在浏览器中强制刷新页面，或关闭旧页面后重新打开。

## 播放器操作

- 节目单工具栏依次提供 **回看 / 返回直播、播放直播、停止、刷新**。
- **回看**：选中可回看的历史节目后显示；回看过程中同一按钮变为 **返回直播**。
- **播放直播**：重新播放当前频道的直播源，默认使用 M3U 中的组播地址和 4022 udpxy。
- **停止**：直播与回看共用，停止播放器并断开当前流。
- 暂停/恢复仍可直接点击视频画面或使用浏览器原生视频控件。
- 播放状态显示在播放器上方、诊断日志入口右侧；诊断日志保留最近 500 条，并支持复制和清空。

## RC2.3 变更

- 合并 `rc1-fix1` 的 HEVC（stream_type `0x24`）Safari 视频包处理：HEVC 视频不再误用 H.264 OpenGopFixer，按 PES 起点建立转发门控，不要求 VPS/SPS/PPS/IRAP 同时出现在同一个 TS 包中。
- 更新 `iptvweb-audio-probe`：加入连续 TS 同步校验、PAT/PMT PSI section 跨包拼接、CRC 和 continuity counter 检查，并将探测读取上限设为 32 MiB、外部读取超时设为 4 秒。
- 保留 RC2.1 精简界面：隐藏顶部操作按钮、状态文字和诊断面板，视频下方仍保留播放/恢复和停止按钮。

## RC2.3 回看功能

> 当前回看复用完整 A/V MSE 管线。桌面浏览器按其解码能力播放；iOS Safari 的 MPEG Audio 独立 mpg123 音频解码仍是直播专用路径，回看音频需要在实机上确认。

- 频道列表中的回看按钮只对能匹配单播 RTSP 地址的频道启用；映射数据来自浙江电信单播 M3U。
- 从频道节目时间轴选择节目进行回看，按节目单中的北京时间起止时间生成 `playseek`；正在播出的节目只回看从节目开始至当前时刻的部分。单次回看仍受 4 小时上限约束。
- 回看使用 `http://路由器:4023/stream?url=...&seek=开始-结束`，通过 Fetch/ReadableStream 将裸 TS 数据交给 mpegts.js。
- 切台、改时间、停止和退出回看时销毁播放器并取消 Fetch；连接失败进行一次重试，过早断流会提示回看不可用。
- 退出回看立即恢复 4022 组播直播；组播出错或连接结束时，有 RTSP 映射则尝试 4023 单播直播兜底。
- iOS 横屏将频道列表设为独立滚动区域，确保末尾频道可滚动到达。

## 测试建议

发布后建议至少检查以下场景：

1. iPhone/iPad Safari：播放 MPEG Audio 普通频道，检查视频、声音、音调和长时间播放。
2. iPhone/iPad Safari：播放 AAC 音轨频道（包括高分辨率频道，如有），确认仍使用正常 A/V 路径。
3. 桌面 Chrome/Edge、Firefox：验证普通频道播放和视频区域点击暂停/恢复。
4. 切换频道、刷新列表、重新初始化和停止播放，确认旧流会关闭且新频道能正常启动。
5. 在升级前后确认原有 LuCI 配置未被覆盖。

不同直播源的编码、随机访问点、时间戳和浏览器硬件解码能力存在差异；RC2.3 保留当前分流与兼容处理，不承诺每个频道在所有设备上均可播放。

## 许可

本项目按 MIT License 发布，完整许可文本见仓库根目录 [`LICENSE`](LICENSE)。第三方依赖各自遵循其上游许可证。

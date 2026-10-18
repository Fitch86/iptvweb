# IPTV Web for OpenWrt — RC1.4

轻量级 OpenWrt LuCI IPTV 网页播放器。通过 M3U 读取频道列表，并使用路由器上的 udpxy HTTP 转发组播 MPEG-TS；浏览器端使用 mpegts.js / Media Source Extensions 播放视频。

> **RC1.4 是测试候选版，不代表所有设备、浏览器和频道组合均已验证。** 当前基线来自仓库 `main` 的 rev4.25。此分支主要清理诊断界面和实验入口，并保留当前 Safari 音轨分流及播放实现。

## 功能

- 在 LuCI 中配置 M3U 播放列表地址。
- 按频道分组显示列表，支持刷新、重新初始化、跳到直播最新帧和停止断流。
- 通过本机 CGI 将 `/udp/组播地址:端口` 转为浏览器可读取的 HTTP MPEG-TS 流。
- 普通桌面浏览器使用原有 mpegts.js A/V 播放路径。
- iOS/iPadOS Safari 根据 PMT 中的音轨类型选择播放路径：
  - MPEG-1/2 Audio（stream_type `0x03/0x04`）：视频使用无音轨 MSE 路径，音频由本地 mpg123-decoder 解码为 PCM，再由 Web Audio 连续播放。
  - AAC（常见 stream_type `0x0F/0x11`）或探测结果未知：保留原生 A/V MSE 路径，不强制切换为 Video-only。
- MP2PCM 会把解码采样率转换到 AudioContext 的输出采样率，避免采样率不一致时出现音频变慢、音调偏低的问题。
- 播放器资源安装到路由器本地；正常播放不依赖浏览器运行时访问 CDN。
- 安装时保留现有 `/etc/config/iptvweb`，避免覆盖用户已配置的 M3U 地址。

## 当前 Safari 路径说明

Safari 路径的关键点不是对所有频道一律禁用 MSE 音轨，而是先判断音轨类型。AAC/未知音轨继续使用原生 A/V；只有确认 MPEG Audio 后，才启用独立 MP2PCM。这样可以保留 HEVC + AAC 4K 频道的原生音视频链路，同时为普通 MPEG Audio 频道提供独立音频解码。

音轨探测接口 `/cgi-bin/iptvweb-audio-probe` 是运行时分流所需的功能组件，**不是可删除的调试探针**。RC1.4 在 RC1.2 的基础上恢复桌面 Chrome 原生视频工具条，Safari 视频过滤器保留所有已识别的视频 PID，并增加 AVS3 stream_type 识别；LuCI 的 udpxy address 字段改为校验完整 host:port，修复 `192.168.1.1:4022` 被 `host` 类型校验拒绝的问题。Safari 普通频道偶发有声无画面仍需在目标设备复测，不能视为已完全解决。RC1.4 重新加入默认关闭的精简诊断面板，可手动开启并复制日志；日志包含 Safari 视频状态、首帧、mpegts.js 关键控制台消息和 TS 过滤统计。诊断关闭时不收集这些日志。能力探测按钮、TS 抓包入口及实验开关仍已移除，但保留正常播放所需的音轨识别和音频解码组件。

## 历史脉络

| 版本阶段 | 主要变化 |
| --- | --- |
| rev4.2–rev4.6 | 修复频道列表脚本运行时异常、播放时未定义函数调用和配置覆盖问题；避免播放期间额外抓取同一条组播流。 |
| rev4.7 | 已知可正常播放浙江卫视 4K 的 A/V 基线：HEVC Main10 3840×2160@50，AAC-LC 48 kHz 双声道；播放参数使用 `isLive=false`、384 KiB stash，默认关闭 `fixAudioTimestampGap`。 |
| rev4.8–rev4.14 | 探索 iOS Safari ManagedMediaSource、实时流参数及 A/V 失败后的兼容路径。不同版本的实验结果不应混为同一个基线。 |
| rev4.16.3–rev4.21 | 以 Safari Video-only 视频路径为基础，逐步验证 MPEG Audio PES 提取和独立音频解码；修复 OpenWrt Lua 5.1 兼容性及连续音频问题。 |
| rev4.23.1 | 将独立 PCM 播放改为 AudioWorklet / ScriptProcessor 环形缓冲方案，改善连续播放与队列控制。 |
| rev4.25 | 修复 MP2PCM 输入采样率与 AudioContext 采样率不一致导致的变慢、变调问题；当前代码进一步按 PMT 音轨类型分流，AAC/未知音轨保留 A/V MSE。 |
| RC1 | 保留当前播放实现，清理诊断界面和手动实验入口。 |
| RC1.1 | 修复无视频的 MPEG Audio 广播频道音频启动；视频 TS 同步改为多包校验；视频画面点击可暂停/继续。4K 和各类广播音频仍需设备复测。 |

## 安装

推荐在 OpenWrt 路由器上以 root 执行仓库中的安装脚本：

```sh
sh install.sh
```

脚本会安装播放器、CGI 和本地音频组件，并尝试下载 mpegts.js 1.8.2 与 mpg123-decoder 1.0.3。首次安装时路由器需要能够访问 jsDelivr 或 unpkg；若下载失败，请在路由器恢复网络访问后重新运行安装脚本。

安装后打开：

```
http://192.168.1.1/iptv/
```

在 LuCI 的 **Services → IPTV Web** 中配置 M3U 地址。升级后若页面仍显示旧版，请在浏览器中强制刷新（桌面浏览器可使用 Ctrl+F5）。

## RC1.4 测试建议

1. **iOS/iPadOS Safari：浙江卫视 4K** — 检查画面、AAC 声音和连续播放是否正常。
2. **iOS/iPadOS Safari：CCTV1 等 MPEG Audio 普通频道** — 检查是否有声、音调和语速是否正常，以及长时间播放是否中断。
3. **桌面 Chrome/Edge、Firefox** — 检查普通频道和 4K 频道的基本播放。
4. 切换频道、停止播放、刷新页面，确认流连接会正确关闭且频道列表仍可用。
5. 检查升级安装是否保留原有 M3U 配置。

RC1.4 页面默认关闭诊断日志。排查 Safari 无画面时，先点页面顶部“诊断日志：关”开启，再重新选择故障频道，等待约 10–20 秒后点“复制日志”，将日志发回。日志包含 UA、MSE/解码器关键消息、视频事件/尺寸/缓冲区、TS 同步和 PID 过滤统计；不会抓取或保存原始视频流。

## 项目结构

- `package/luci-app-iptvweb/`：LuCI/OpenWrt 包定义和运行文件。
- `package/luci-app-iptvweb/files/www/iptv/index.html`：网页播放器。
- `package/luci-app-iptvweb/files/www/cgi-bin/`：M3U、MPEG-TS 转发与音频相关 CGI。
- `install.sh`：面向现有 OpenWrt 系统的安装脚本。

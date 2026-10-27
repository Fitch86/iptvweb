# IPTV Web for OpenWrt — RC2.0

轻量级 OpenWrt LuCI IPTV 网页播放器。通过 M3U 频道列表和路由器上的 udpxy 接收组播 MPEG-TS，并在浏览器中播放。

> **版本：RC2.0（包版本 `0.2.2-rc2.0`）**  
> RC2.0 基于 `rc1-fix1` 分支整理发布，保留该分支已经调整的 iOS/iPadOS Safari 播放路径和桌面浏览器交互修复。正式界面不显示诊断日志面板、日志复制/清空按钮或实验入口。

## 功能

- 通过 LuCI 配置 M3U 播放列表 URL、udpxy 地址、缓存文件和缓存有效期。
- 自动读取并解析 M3U，按频道分组展示频道名称和台标。
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
| 页面标题与播放器页头 | `RC2.0` |
| 页面内部版本常量 | `RC2.0` |
| OpenWrt 包版本 | `0.2.2-rc2.0` |
| 安装脚本输出 | `0.2.2-rc2.0` |

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
- **M3U cache TTL / cache file**：频道列表缓存设置。

如果升级后仍看到旧页面，请在浏览器中强制刷新页面，或关闭旧页面后重新打开。

## 播放器操作

- **刷新**：重新读取 M3U 频道列表。
- **跳到最新帧**：跳到当前已缓冲区间的末尾附近，适用于直播缓冲落后时。
- **重新初始化**：重新创建当前频道的播放器与流连接。
- **停止并断开**：停止播放并关闭当前流。
- **播放 / 恢复**：在视频区域下方使用该按钮恢复或暂停播放；支持浏览器原生视频控件的设备仍可使用原生控件。

## 测试建议

发布后建议至少检查以下场景：

1. iPhone/iPad Safari：播放 MPEG Audio 普通频道，检查视频、声音、音调和长时间播放。
2. iPhone/iPad Safari：播放 AAC 音轨频道（包括高分辨率频道，如有），确认仍使用正常 A/V 路径。
3. 桌面 Chrome/Edge、Firefox：验证普通频道播放和视频区域点击暂停/恢复。
4. 切换频道、刷新列表、重新初始化和停止播放，确认旧流会关闭且新频道能正常启动。
5. 在升级前后确认原有 LuCI 配置未被覆盖。

不同直播源的编码、随机访问点、时间戳和浏览器硬件解码能力存在差异；RC2.0 保留当前分流与兼容处理，不承诺每个频道在所有设备上均可播放。

## 许可

本项目使用 MIT License。详情请参阅仓库中的 `LICENSE` 文件。

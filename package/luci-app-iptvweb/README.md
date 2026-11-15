# luci-app-iptvweb 0.2.2-rc1.3

本目录为 OpenWrt/LuCI 软件包。项目说明、安装步骤、Safari 音轨分流机制、历史版本脉络和 RC1 测试清单请参阅仓库根目录 [README.md](../../README.md)。

RC1.5 以 RC1 的 rev4.25 播放基线为基础，保留默认关闭、可手动开启并复制的精简诊断面板；修正 Chrome 视频画面点击与原生默认动作冲突；能力探测按钮、TS 分析/抓包入口和播放实验开关仍移除；保留播放状态提示、正常停止/恢复操作、Safari PMT 音轨识别、MPEG Audio 独立 MP2PCM，以及 AAC/未知音轨的原生 A/V MSE 路径。

RC1.5 保留 RC1.2 的广播暂停/继续修复，恢复桌面 Chrome 原生视频工具条；Safari 视频过滤器现在保留全部已识别的视频 PID，并补充 AVS3 类型。LuCI 的 udpxy 字段接受并校验 host:port，例如 192.168.1.1:4022。Safari 普通频道偶发有声无画面仍需复测；可开启精简诊断日志收集 video/MSE/TS PID 相关信息。此版本用于测试，不应把尚未在目标设备上验证的组合视为已保证兼容。

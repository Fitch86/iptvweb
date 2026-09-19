# luci-app-iptvweb 0.2.2-rev4.2

长连接直播代理版。

- 浏览器到 /cgi-bin/iptvweb-stream 保持长连接。
- udpxy 上游 HTTP 会话断开时自动重连。
- 安装时将 uhttpd.main.script_timeout 设置为 86400 秒并重启 uhttpd。
- mpegts.js 本地加载。

# luci-app-iptvweb

A lightweight OpenWrt 25.12 LuCI IPTV web player for LAN clients.

Features:
- Configure an M3U URL and udpxy address in LuCI.
- Fetches the M3U server-side, so browser CORS is not required.
- Replaces `{{your_udpxy_address}}` with the configured udpxy address.
- Groups channels by `group-title`, displays logos.
- Uses mpegts.js in the browser to play udpxy MPEG-TS streams without transcoding.
- Optional EPG URL is read from `x-tvg-url`; the first version exposes it as a link and keeps the M3U metadata intact.

Target: OpenWrt 25.12+ / LuCI.

Install a locally built APK on OpenWrt 25.12 with:
    apk add --allow-untrusted /tmp/luci-app-iptvweb_0.1.0-r1_all.apk

For development/building, use an OpenWrt 25.12 SDK or buildroot. See package/luci-app-iptvweb/Makefile.

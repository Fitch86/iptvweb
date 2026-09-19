#!/bin/sh
set -eu

BASE="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
FILES="$BASE/package/luci-app-iptvweb/files"

[ "$(id -u)" = 0 ] || { echo "Run as root"; exit 1; }

cp -f "$FILES/etc/config/iptvweb" /etc/config/iptvweb
mkdir -p /etc/uci-defaults /usr/bin /www/iptv /www/cgi-bin \
  /usr/share/luci/menu.d /usr/share/rpcd/acl.d \
  /www/luci-static/resources/view /www/luci-static/resources/iptvweb

cp -f "$FILES/usr/bin/iptvweb-fetch" /usr/bin/iptvweb-fetch
cp -f "$FILES/www/iptv/index.html" /www/iptv/index.html
cp -f "$FILES/www/cgi-bin/iptvweb-m3u" /www/cgi-bin/iptvweb-m3u
cp -f "$FILES/www/cgi-bin/iptvweb-stream" /www/cgi-bin/iptvweb-stream
cp -f "$FILES/usr/share/luci/menu.d/luci-app-iptvweb.json" /usr/share/luci/menu.d/luci-app-iptvweb.json
cp -f "$FILES/usr/share/rpcd/acl.d/luci-app-iptvweb.json" /usr/share/rpcd/acl.d/luci-app-iptvweb.json
cp -f "$FILES/www/luci-static/resources/view/iptvweb.js" /www/luci-static/resources/view/iptvweb.js
cp -f "$FILES/www/luci-static/resources/iptvweb/mpegts.min.js" /www/luci-static/resources/iptvweb/mpegts.min.js

chmod 0755 /usr/bin/iptvweb-fetch /www/cgi-bin/iptvweb-m3u /www/cgi-bin/iptvweb-stream
[ -x /www/cgi-bin/iptvweb-stream ] || { echo "ERROR: iptvweb-stream was not installed" >&2; exit 1; }

/etc/init.d/rpcd restart 2>/dev/null || true
/etc/init.d/uhttpd restart 2>/dev/null || true

echo
echo "Installed."
echo "LuCI: Services -> IPTV Web"
echo "Player: http://192.168.1.1/iptv/"
echo
echo "Note: IPTV streams are proxied through the same-origin /cgi-bin/iptvweb-stream endpoint to avoid CORS."

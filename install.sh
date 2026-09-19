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

# Fetch the full mpegts.js 1.8.0 once during installation. The browser never
# loads jsDelivr/unpkg at runtime, so Edge/Chrome tracking prevention is irrelevant.
TMP="/tmp/mpegts.min.js.iptvweb"
URL1="https://cdn.jsdelivr.net/npm/mpegts.js@1.8.0/dist/mpegts.min.js"
URL2="https://unpkg.com/mpegts.js@1.8.0/dist/mpegts.min.js"
FETCHED=0
if command -v uclient-fetch >/dev/null 2>&1; then
    uclient-fetch -q -O "$TMP" "$URL1" 2>/dev/null && FETCHED=1 || true
    [ "$FETCHED" = 1 ] || (uclient-fetch -q -O "$TMP" "$URL2" 2>/dev/null && FETCHED=1 || true)
elif command -v wget >/dev/null 2>&1; then
    wget -q -O "$TMP" "$URL1" && FETCHED=1 || true
    [ "$FETCHED" = 1 ] || (wget -q -O "$TMP" "$URL2" && FETCHED=1 || true)
fi
if [ "$FETCHED" = 1 ] && [ -s "$TMP" ] && [ "$(wc -c < "$TMP")" -gt 100000 ] && grep -q 'mpegts' "$TMP" 2>/dev/null; then
    mv -f "$TMP" /www/luci-static/resources/iptvweb/mpegts.min.js
else
    rm -f "$TMP"
    echo "ERROR: could not download mpegts.js 1.8.0. Router needs Internet access during installation." >&2
    exit 1
fi

chmod 0755 /usr/bin/iptvweb-fetch /www/cgi-bin/iptvweb-m3u /www/cgi-bin/iptvweb-stream
[ -x /www/cgi-bin/iptvweb-stream ] || { echo "ERROR: iptvweb-stream was not installed" >&2; exit 1; }

/etc/init.d/rpcd restart 2>/dev/null || true
/etc/init.d/uhttpd restart 2>/dev/null || true

echo
echo "Installed 0.2.2-rev3.3."
echo "LuCI: Services -> IPTV Web"
echo "Player: http://192.168.1.1/iptv/"
echo
echo "Note: mpegts.js 1.8.0 is stored locally; no CDN request is made by the player."
echo "Note: IPTV streams are proxied through the same-origin /cgi-bin/iptvweb-stream endpoint to avoid CORS."

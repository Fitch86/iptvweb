#!/bin/sh
set -eu

BASE="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
if [ -d "$BASE/package/luci-app-iptvweb/files" ]; then
  FILES="$BASE/package/luci-app-iptvweb/files"
elif [ -d "$BASE/files" ]; then
  FILES="$BASE/files"
else
  echo "ERROR: files directory not found" >&2; exit 1
fi

[ "$(id -u)" = 0 ] || { echo "Run as root"; exit 1; }

# Never clobber a live UCI config: rev4.2 overwrote custom M3U URLs.
if [ ! -f /etc/config/iptvweb ]; then
  cp -f "$FILES/etc/config/iptvweb" /etc/config/iptvweb
fi

mkdir -p /etc/uci-defaults /usr/bin /www/iptv /www/cgi-bin \
  /usr/share/luci/menu.d /usr/share/rpcd/acl.d \
  /www/luci-static/resources/view /www/luci-static/resources/iptvweb

cp -f "$FILES/usr/bin/iptvweb-fetch" /usr/bin/iptvweb-fetch
cp -f "$FILES/www/iptv/index.html" /www/iptv/index.html
cp -f "$FILES/www/cgi-bin/iptvweb-m3u" /www/cgi-bin/iptvweb-m3u
cp -f "$FILES/www/cgi-bin/iptvweb-stream" /www/cgi-bin/iptvweb-stream
cp -f "$FILES/www/cgi-bin/iptvweb-audio" /www/cgi-bin/iptvweb-audio
cp -f "$FILES/www/cgi-bin/iptvweb-capture" /www/cgi-bin/iptvweb-capture
cp -f "$FILES/usr/share/luci/menu.d/luci-app-iptvweb.json" /usr/share/luci/menu.d/luci-app-iptvweb.json
cp -f "$FILES/usr/share/rpcd/acl.d/luci-app-iptvweb.json" /usr/share/rpcd/acl.d/luci-app-iptvweb.json
cp -f "$FILES/www/luci-static/resources/view/iptvweb.js" /www/luci-static/resources/view/iptvweb.js

# Keep a working local mpegts.js across reinstalls. Only replace with the
# stub if no real copy exists yet; install then tries to download 1.8.0.
if [ ! -s /www/luci-static/resources/iptvweb/mpegts.min.js ] || \
   [ "$(wc -c < /www/luci-static/resources/iptvweb/mpegts.min.js)" -lt 100000 ]; then
  cp -f "$FILES/www/luci-static/resources/iptvweb/mpegts.min.js" /www/luci-static/resources/iptvweb/mpegts.min.js
fi

if command -v uci >/dev/null 2>&1; then
    uci -q set uhttpd.main.script_timeout='86400' || true
    uci -q commit uhttpd || true
fi

TMP="/tmp/mpegts.min.js.iptvweb"
URL1="https://cdn.jsdelivr.net/npm/mpegts.js@1.8.2/dist/mpegts.min.js"
URL2="https://unpkg.com/mpegts.js@1.8.2/dist/mpegts.min.js"
FETCHED=0
if command -v uclient-fetch >/dev/null 2>&1; then
    uclient-fetch -q -T 20 -O "$TMP" "$URL1" 2>/dev/null && FETCHED=1 || true
    [ "$FETCHED" = 1 ] || (uclient-fetch -q -T 20 -O "$TMP" "$URL2" 2>/dev/null && FETCHED=1 || true)
elif command -v wget >/dev/null 2>&1; then
    wget -q -T 20 -O "$TMP" "$URL1" && FETCHED=1 || true
    [ "$FETCHED" = 1 ] || (wget -q -T 20 -O "$TMP" "$URL2" && FETCHED=1 || true)
fi
if [ "$FETCHED" = 1 ] && [ -s "$TMP" ] && [ "$(wc -c < "$TMP")" -gt 100000 ] && grep -q 'mpegts' "$TMP" 2>/dev/null; then
    mv -f "$TMP" /www/luci-static/resources/iptvweb/mpegts.min.js
else
    rm -f "$TMP"
    if [ -s /www/luci-static/resources/iptvweb/mpegts.min.js ] && \
       [ "$(wc -c < /www/luci-static/resources/iptvweb/mpegts.min.js)" -gt 100000 ]; then
        echo "NOTE: could not refresh mpegts.js 1.8.2; keeping the existing local copy."
    else
        echo "ERROR: could not download mpegts.js 1.8.2. Router needs Internet access during installation." >&2
        exit 1
    fi
fi

chmod 0755 /usr/bin/iptvweb-fetch /www/cgi-bin/iptvweb-m3u /www/cgi-bin/iptvweb-stream /www/cgi-bin/iptvweb-audio /www/cgi-bin/iptvweb-capture
[ -x /www/cgi-bin/iptvweb-stream ] || { echo "ERROR: iptvweb-stream was not installed" >&2; exit 1; }
[ -x /www/cgi-bin/iptvweb-m3u ] || { echo "ERROR: iptvweb-m3u was not installed" >&2; exit 1; }
[ -x /www/cgi-bin/iptvweb-audio ] || { echo "ERROR: iptvweb-audio was not installed" >&2; exit 1; }

/etc/init.d/rpcd restart 2>/dev/null || true
/etc/init.d/uhttpd restart 2>/dev/null || true

echo
echo "Installed 0.2.2-rev4.16."
echo "LuCI: Services -> IPTV Web"
echo "Player: http://192.168.1.1/iptv/"
echo
echo "rev4.16: Safari H.264 video MSE + independent native MP3 audio experiment; M3U config is preserved;"
echo "        mpegts.js 1.8.2 stays local; long-lived CGI still uses script_timeout=86400."
echo "Force-refresh the player page (Ctrl+F5) after installing."
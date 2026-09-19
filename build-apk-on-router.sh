#!/bin/sh
set -eu
ROOT="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
OUT="${ROOT}/luci-app-iptvweb_0.2.0-r1_all.apk"
STAGE="${ROOT}/.stage"
rm -rf "$STAGE"
mkdir -p "$STAGE"

# Copy package payload
cp -a "$ROOT/package/luci-app-iptvweb/files/." "$STAGE/"

# The OpenWrt apk command in 25.12 includes apk mkpkg in current builds.
apk mkpkg \
  --info name:luci-app-iptvweb \
  --info version:0.2.0-r1 \
  --info arch:all \
  --info license:MIT \
  --info description:"Lightweight LuCI IPTV web player using M3U and udpxy" \
  --files "$STAGE" \
  --output "$OUT"

echo "Built: $OUT"
echo "Install on OpenWrt 25.12+: apk add --allow-untrusted $OUT"

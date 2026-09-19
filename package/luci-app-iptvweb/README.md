# luci-app-iptvweb 0.2.2-rev3.3

OpenWrt 25.12+ LAN IPTV web player for an existing udpxy service.

## rev3.3
- `isLive=false` unchanged.
- `stashInitialSize=1MB` unchanged.
- HTML5 autoplay is disabled completely; playback is started only by the page's explicit `player.play()` call.
- Pending delayed-start timers are canceled when the video is paused before explicit playback.
- First-frame/first-playing diagnostics use relative test times.
- `SOURCE=unexpected-autoplay` is logged if a play event occurs before the page's explicit play call.
- The 0/1/2/3/5-second startup-buffer selector remains for controlled A/B testing.
- mpegts.js 1.8.0 remains locally installed; no CDN is used at runtime.

Recommended first test: 0s, 2s, 5s, two repeats per setting.

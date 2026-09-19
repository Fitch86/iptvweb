# luci-app-iptvweb 0.2.2

OpenWrt 25.12+ LAN IPTV web player for an existing udpxy service.

## 0.2.2 changes
- Uses mpegts.js 1.8.0 **locally at runtime**. `install.sh` downloads the full minified distribution once during installation; the browser never loads jsDelivr/unpkg.
- Disables `liveBufferLatencyChasing` and `liveSync`, avoiding aggressive live-position chasing that can cause freezes/jumps on some MPEG-TS live streams.
- Keeps the IO stash buffer and raises the initial stash to 512 KiB.
- Enables the mpegts.js worker paths on modern browsers.
- Enables `fixAudioTimestampGap` and conservative SourceBuffer cleanup.
- Cleans up the previous player before channel switching and avoids the old `play()`/`pause()` race as much as possible.
- On Safari, if the first MSE attempt reports a media-source/format error, retries once as video-only. This is useful for streams whose audio codec cannot be put into Safari's MSE SourceBuffer.
- H.265/HEVC remains dependent on browser/OS codec support. Chrome/Safari may play channels that Edge cannot.

## Install

The router needs Internet access **once** while running `install.sh`, because the complete mpegts.js 1.8.0 file is downloaded into `/www/luci-static/resources/iptvweb/mpegts.min.js`.

The runtime player does not contact a CDN.

## Configuration
LuCI -> Services -> IPTV Web:
- M3U playlist URL
- udpxy address, e.g. `192.168.1.1:4022`

Player: `http://192.168.1.1/iptv/`

The server-side proxy only accepts IPv4 multicast destinations (224.0.0.0/4) and uses the configured udpxy endpoint.


## rev3.2 A/B 延迟播放测试

- 保持 isLive=false、Worker 配置不变。
- stashInitialSize 固定为 1MB（根据 rev3.1 实测选择）。
- 播放器顶部“启动缓冲”可选择 0/1/2/3/5 秒。
- 0 秒：立即 play()，作为基线。
- 1/2/3/5 秒：等待 video.buffered 的 bufferAhead 达到目标后才首次调用 player.play()。
- 每次切换目标后重新选择 CCTV1，使一次测试只对应一个启动阈值。
- 日志会记录 `DELAY play` 轮询、实际 `start play()` 时的 bufferAhead，以及后续 waiting。

建议测试顺序：0s → 1s → 2s → 3s → 5s；每档至少重复 2-3 次。重点比较首次 waiting 是否消失，以及首次 play 到 firstFrame/playing 的总时间。

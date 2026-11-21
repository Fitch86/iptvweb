# IPTVWeb 0.3.0 HTTP(S) Proxy

The 0.3.0 branch adds a standalone CGI proxy. It does not change the RC2.4 player,
multicast/unicast playback paths, or the RTSP relay.

## Endpoint

`/cgi-bin/iptvweb-proxy?url=<URL-encoded-http-or-https-URL>`

Examples (replace the host and upstream URL):

- M3U subscription:
  `http://192.168.1.1/cgi-bin/iptvweb-proxy?url=https%3A%2F%2Fexample.org%2Fiptv.m3u`
- MPEG-TS:
  `http://192.168.1.1/cgi-bin/iptvweb-proxy?url=http%3A%2F%2Fmedia.example.org%2Flive.ts`
- HLS:
  `http://192.168.1.1/cgi-bin/iptvweb-proxy?url=https%3A%2F%2Fmedia.example.org%2Fmaster.m3u8`

M3U media URLs are rewritten through this endpoint. HLS playlists additionally
rewrite relative/absolute child playlists, segments, initialization maps and
key URI attributes. The proxy streams non-playlist bodies in chunks and forwards
a valid browser Range header. An optional `ua` query parameter sets the upstream
User-Agent (maximum 256 characters).

## Initial security boundary

- The CGI accepts requests only from private/loopback client addresses.
- Upstream schemes are restricted to HTTP and HTTPS.
- URL credentials, localhost names, private, loopback, link-local, multicast,
  reserved and unspecified destination addresses are rejected.
- DNS answers are validated and the selected public IP is pinned for the
  outbound connection; redirects are revalidated and pinned independently.
- System TLS certificate and hostname verification remain enabled.
- Environment proxy settings are ignored; no user-supplied Cookie, Host or
  proxy-auth headers are forwarded.

This intentionally blocks private/LAN upstreams, including some ISP IPTV
endpoints. A narrowly scoped allowlist can be designed later if private upstream
support is required; do not disable destination validation globally.

## Runtime dependencies

The package declares `python3-light`, `python3-urllib` and `python3-ssl`.
The system CA bundle must be installed for HTTPS validation.

## Manual smoke tests

Run from a LAN client after installing the package:

1. Fetch a public M3U and verify that its media URLs point back to
   `/cgi-bin/iptvweb-proxy?url=...`.
2. Fetch a public MPEG-TS URL and verify continuous bytes; repeat with a Range
   request and check the upstream 206/Content-Range response.
3. Fetch an HLS master/media playlist and verify that child playlist, segment,
   map and key URIs all point back to the proxy.
4. Try an HTTP redirect to a public host, then to a private IP; the latter must
   be rejected.
5. Try loopback/private destinations and a non-LAN client; both must be denied.
6. Stop the client during a TS stream and confirm the upstream connection closes.

These are test instructions, not claims that the package has already been
built or exercised on an MT6000. Router installation and live-stream validation
remain pending.

'use strict';
'require view';
'require form';

return view.extend({
    render: function() {
        var m, s, o;

        m = new form.Map('iptvweb', _('IPTV Web'),
            _('Configure the M3U playlist and the udpxy address used by the LAN IPTV web player.'));

        s = m.section(form.NamedSection, 'main', 'iptvweb', _('Player settings'));
        s.anonymous = true;

        o = s.option(form.Value, 'm3u_url', _('M3U playlist URL'));
        o.datatype = 'string';
        o.rmempty = false;
        o.description = _('Example: https://myepg.org/api/subscribe/multicast/m3u?udpxy=192.168.1.1:4022');

        o = s.option(form.Value, 'udpxy', _('udpxy address'));
        o.datatype = 'host';
        o.rmempty = false;
        o.description = _('Host:port, for example 192.168.1.1:4022. The template {{your_udpxy_address}} in the M3U is replaced with this value.');

        o = s.option(form.Value, 'cache_ttl', _('M3U cache TTL (seconds)'));
        o.datatype = 'uinteger';
        o.default = '21600';

        o = s.option(form.Value, 'cache', _('M3U cache file'));
        o.datatype = 'string';
        o.default = '/tmp/iptvweb.m3u';
        o.rmempty = false;

        return m.render();
    }
});
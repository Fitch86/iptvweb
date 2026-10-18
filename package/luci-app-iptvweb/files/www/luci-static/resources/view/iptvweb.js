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
        // LuCI's built-in "host" validator rejects the required :port suffix.
        // Validate the full host:port value instead.
        o.datatype = 'string';
        o.rmempty = false;
        o.description = _('Host:port, for example 192.168.1.1:4022. The template {{your_udpxy_address}} in the M3U is replaced with this value.');
        o.validate = function(section_id, value) {
            var match = value.match(/^(\[[0-9a-fA-F:.]+\]|[^:\s]+):([0-9]{1,5})$/);
            if (!match)
                return _('Enter a valid hostname or IP address followed by :port, e.g. 192.168.1.1:4022.');

            var host = match[1];
            var port = Number(match[2]);
            if (port < 1 || port > 65535)
                return _('Port must be between 1 and 65535.');

            if (host.charAt(0) === '[') {
                if (host.indexOf(':') < 0)
                    return _('Enter a valid IPv6 address in brackets.');
                return true;
            }

            if (/^[0-9.]+$/.test(host)) {
                var octets = host.split('.');
                if (octets.length !== 4 || octets.some(function(part) {
                    return !/^([0-9]{1,3})$/.test(part) || Number(part) > 255;
                }))
                    return _('Enter a valid IPv4 address.');
                return true;
            }

            if (host.length > 253 || !/^(?=.{1,253}$)[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)*$/.test(host))
                return _('Enter a valid hostname or IP address.');
            return true;
        };

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
include $(TOPDIR)/rules.mk

PKG_NAME:=luci-app-iptvweb
PKG_VERSION:=0.2.2-rev4.4
PKG_RELEASE:=1

PKG_LICENSE:=MIT
PKG_MAINTAINER:=OpenWrt IPTV Web contributors

include $(INCLUDE_DIR)/package.mk

define Package/luci-app-iptvweb
  SECTION:=luci
  CATEGORY:=LuCI
  SUBMENU:=Applications
  TITLE:=IPTV Web Player
  DEPENDS:=+uhttpd +luci-base
endef

define Package/luci-app-iptvweb/description
Lightweight LuCI-configured IPTV web player using M3U and udpxy.
endef

define Build/Compile
endef

define Package/luci-app-iptvweb/install
	$(INSTALL_DIR) $(1)/etc/config
	$(INSTALL_CONF) ./files/etc/config/iptvweb $(1)/etc/config/iptvweb

	$(INSTALL_DIR) $(1)/etc/uci-defaults
	$(INSTALL_BIN) ./files/etc/uci-defaults/99-iptvweb $(1)/etc/uci-defaults/99-iptvweb

	$(INSTALL_DIR) $(1)/usr/bin
	$(INSTALL_BIN) ./files/usr/bin/iptvweb-fetch $(1)/usr/bin/iptvweb-fetch

	$(INSTALL_DIR) $(1)/www/cgi-bin
	$(INSTALL_BIN) ./files/www/cgi-bin/iptvweb-m3u $(1)/www/cgi-bin/iptvweb-m3u
	$(INSTALL_BIN) ./files/www/cgi-bin/iptvweb-stream $(1)/www/cgi-bin/iptvweb-stream
	$(INSTALL_BIN) ./files/www/cgi-bin/iptvweb-capture $(1)/www/cgi-bin/iptvweb-capture

	$(INSTALL_DIR) $(1)/www/iptv
	$(INSTALL_DATA) ./files/www/iptv/index.html $(1)/www/iptv/index.html

	$(INSTALL_DIR) $(1)/usr/share/luci/menu.d
	$(INSTALL_DATA) ./files/usr/share/luci/menu.d/luci-app-iptvweb.json $(1)/usr/share/luci/menu.d/luci-app-iptvweb.json

	$(INSTALL_DIR) $(1)/usr/share/rpcd/acl.d
	$(INSTALL_DATA) ./files/usr/share/rpcd/acl.d/luci-app-iptvweb.json $(1)/usr/share/rpcd/acl.d/luci-app-iptvweb.json

	$(INSTALL_DIR) $(1)/www/luci-static/resources/view
	$(INSTALL_DATA) ./files/www/luci-static/resources/view/iptvweb.js $(1)/www/luci-static/resources/view/iptvweb.js

	$(INSTALL_DIR) $(1)/www/luci-static/resources/iptvweb
	$(INSTALL_DATA) ./files/www/luci-static/resources/iptvweb/mpegts.min.js $(1)/www/luci-static/resources/iptvweb/mpegts.min.js
endef

$(eval $(call BuildPackage,luci-app-iptvweb))

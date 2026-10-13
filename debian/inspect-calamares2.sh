#!/bin/bash
CH=/root/xenonos-lb/chroot
echo "== branding dizini"
ls -la $CH/etc/calamares/branding/debian | head -30
echo "== branding.desc"
cat $CH/etc/calamares/branding/debian/branding.desc | head -90
echo "== calamares-install-debian (Exec)"
cat $CH/usr/bin/calamares-install-debian 2>/dev/null | head -20
echo "== desktop"
cat $CH/usr/share/applications/calamares-install-debian.desktop
echo "== ikonlar install-debian"
find $CH/usr/share/icons $CH/usr/share/pixmaps -iname '*install-debian*' 2>/dev/null | head
echo "== locale/keyboard/welcome modul ayarlari"
cat $CH/etc/calamares/modules/welcome.conf 2>/dev/null | grep -v '^#' | grep -v '^$' | head -30
cat $CH/etc/calamares/modules/users.conf 2>/dev/null | grep -v '^#' | grep -v '^$' | head -30
echo "== settings.conf ustu"
sed -n 1,47p $CH/etc/calamares/settings.conf | grep -v '^#' | grep -v '^$'

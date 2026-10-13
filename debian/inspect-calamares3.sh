#!/bin/bash
CH=/root/xenonos-lb/chroot
echo "== packages.conf"; grep -v '^#' $CH/etc/calamares/modules/packages.conf | grep -v '^$'
echo "== kurulu live-* paketleri"
chroot $CH dpkg -l 'live-*' 'calamares*' 2>/dev/null | awk '/^ii/ {print $2, $3}'
echo "== bootloader.conf"; grep -v '^#' $CH/etc/calamares/modules/bootloader.conf | grep -v '^$' | head -20
echo "== diger modul dosyalari (users/displaymanager)"; grep -v '^#' $CH/etc/calamares/modules/displaymanager.conf | grep -v '^$' | head
echo "== sources-final / sources-media"; ls $CH/etc/calamares/modules | head -30; ls $CH/usr/lib/calamares/modules | head -60

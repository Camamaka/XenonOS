#!/bin/bash
CH=/root/xenonos-lb/chroot
echo "== bootloader-config yardimci"
cat $CH/usr/share/calamares/helpers/calamares-bootloader-config 2>/dev/null | head -90
echo "== calamares paketleri / ayarlar"
ls $CH/etc/calamares $CH/etc/calamares/modules 2>/dev/null | head -50
echo "== settings.conf (branding, sequence)"
grep -nE "branding|^  - |bootloader|grubcfg|unpackfs|packages|users|welcome" $CH/etc/calamares/settings.conf | head -50
echo "== branding dizinleri"
ls $CH/usr/share/calamares/branding $CH/etc/calamares/branding 2>/dev/null
echo "== desktop dosyalari (calamares)"
ls $CH/usr/share/applications | grep -i -E "calam|install"
grep -n "^Name\|^Icon\|^Exec" $CH/usr/share/applications/*calamares*.desktop 2>/dev/null | head
echo "== grub paketleri chroot'ta var mi"
for p in grub-efi grub-efi-amd64 grub-efi-amd64-bin grub-pc-bin grub-common grub2-common shim-signed efibootmgr os-prober; do
  if chroot $CH dpkg -s $p >/dev/null 2>&1; then echo "kurulu: $p"; else echo "YOK: $p"; fi
done

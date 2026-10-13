#!/bin/bash
B=/usr/share/live/build/bootloaders
echo "== splash.svg (sablon)"; wc -c $B/splash.svg; grep -n "<text\|tspan\|@\|Debian\|<image\|<use" $B/splash.svg | head -30 | cut -c1-200
echo "== binary agacindaki cfg dosyalari"; find /root/xenonos-lb/binary -name '*.cfg' | head -20
echo "== isolinux live.cfg"; cat /root/xenonos-lb/binary/isolinux/live.cfg 2>/dev/null | head -20
echo "== stdmenu.cfg"; cat /root/xenonos-lb/binary/isolinux/stdmenu.cfg 2>/dev/null | head -20
echo "== menu.cfg"; cat /root/xenonos-lb/binary/isolinux/menu.cfg 2>/dev/null | head -20
echo "== EFI grub.cfg (efi.img icinde degil; kok)"; find /root/xenonos-lb/binary -maxdepth 3 -name 'grub.cfg*' -o -maxdepth 3 -name 'live.cfg'
echo "== binary icindeki dizinler"; ls /root/xenonos-lb/binary /root/xenonos-lb/binary/boot /root/xenonos-lb/binary/EFI 2>/dev/null | head -30
echo "== config/bootloaders (bizim)"; ls /root/xenonos-lb/config/bootloaders 2>/dev/null
echo "== live-build bootloader aramasi: splash nereden"
grep -rn "splash" /usr/lib/live/build/lb_binary_syslinux 2>/dev/null | head -8 | cut -c1-160
grep -rn "Debian GNU/Linux\|PRODUCT\|title" /usr/lib/live/build/lb_binary_syslinux 2>/dev/null | head -10 | cut -c1-180

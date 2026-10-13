#!/bin/bash
LB=/root/xenonos-lb
echo "== boot hook calistimi?"; grep -n "xenonos\] boot menu" /root/xenonos-iso-build.log | head -3
echo "== chroot hook calistimi?"; grep -n "\[xenonos\]" /root/xenonos-iso-build.log | head -12 | cut -c1-120
echo "== os-release (chroot)"; cat $LB/chroot/usr/lib/os-release 2>/dev/null | head -20
echo "== /etc/os-release baglantisi"; ls -la $LB/chroot/etc/os-release
echo "== issue"; cat $LB/chroot/etc/issue
echo "== isolinux menusu"; ls $LB/binary/isolinux 2>/dev/null | head -20
grep -rn "Debian" $LB/binary/isolinux/*.cfg 2>/dev/null | head -5 | cut -c1-140
echo "== grub cfg"; grep -rn "Debian\|XenonOS" $LB/binary/boot/grub/*.cfg 2>/dev/null | head -5 | cut -c1-140
echo "== hook dizinleri"; ls $LB/config/hooks/ $LB/config/hooks/live 2>/dev/null
echo "== extension kuruldu mu"; ls $LB/chroot/usr/share/gnome-shell/extensions/ | head
echo "== GDM autologin"; grep -n "Automatic" $LB/chroot/etc/gdm3/daemon.conf 2>/dev/null | head -4
echo "== dconf db"; ls -la $LB/chroot/etc/dconf/db/ 2>/dev/null | head

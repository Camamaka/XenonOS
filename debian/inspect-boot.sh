#!/bin/bash
B=/usr/share/live/build/bootloaders
echo "== bootloaders directory"; ls $B
echo "== grub-efi / grub-pc templates"
for d in grub-efi grub-pc grub; do [ -d $B/$d ] && { echo "--- $d"; find $B/$d -maxdepth 3 | head -40; }; done
echo "== theme.txt"
find $B -name 'theme.txt' | head -3
T=$(find $B -name 'theme.txt' | head -1)
[ -n "$T" ] && cat "$T" | head -50
echo "== grub.cfg template"
find $B -name 'grub.cfg*' | head
G=$(find $B -name 'grub.cfg' | head -1); [ -n "$G" ] && cat "$G" | head -40
echo "== isolinux/syslinux templates"
find $B/syslinux -maxdepth 2 2>/dev/null | head -20
echo "== generated binary tree (grub)"
find /root/xenonos-lb/binary/boot/grub -maxdepth 2 | head -30
grep -n "menuentry\|title-text\|Debian" /root/xenonos-lb/binary/boot/grub/grub.cfg 2>/dev/null | head -10
cat /root/xenonos-lb/binary/boot/grub/live-theme/theme.txt 2>/dev/null | head -30
echo "== EFI boot grub.cfg (inside the ISO)"
find /root/xenonos-lb/binary -name 'grub*.cfg' | head

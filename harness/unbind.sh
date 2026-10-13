#!/bin/bash
# chroot icin yapilan tum baglantilari coz (rm -rf rootfs'ten once calistirilmali)
for m in $(awk -v p="/root/work/rootfs/" 'index($2, p) == 1 { print $2 }' /proc/mounts | sort -r); do
    umount -l "$m" 2>/dev/null && echo "cozuldu: $m"
done
true

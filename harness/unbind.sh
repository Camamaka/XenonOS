#!/bin/bash
# unbind everything bound for the chroot (must run before rm -rf rootfs)
for m in $(awk -v p="/root/work/rootfs/" 'index($2, p) == 1 { print $2 }' /proc/mounts | sort -r); do
    umount -l "$m" 2>/dev/null && echo "unbound: $m"
done
true

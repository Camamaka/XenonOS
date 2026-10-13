#!/bin/bash
# Gorsel test duzenegi: ISO'nun taban dosya sistemini (/root/work/rootfs) chroot ile acar,
# WSLg ekranini icine baglar ve uygulamayi Windows masaustunde calistirir.
# GUVENLIK: yalnizca /proc /sys /dev /tmp/.X11-unix /mnt/wslg baglanir (uygulama kaynaklari BAGLANMAZ).
# Isi bitince unbind.sh calistir; derleme betigi de rootfs'i silmeden once bunlari cozer.
set -e
R=/root/work/rootfs
mountpoint -q $R/proc || mount -t proc proc $R/proc
mountpoint -q $R/sys  || mount -t sysfs sys $R/sys
mountpoint -q $R/dev  || mount --bind /dev $R/dev
mkdir -p $R/tmp/.X11-unix $R/mnt/wslg
mountpoint -q $R/tmp/.X11-unix || mount --bind /tmp/.X11-unix $R/tmp/.X11-unix
mountpoint -q $R/mnt/wslg || mount --bind /mnt/wslg $R/mnt/wslg
cp -f /etc/resolv.conf $R/etc/resolv.conf 2>/dev/null || true
mkdir -p $R/root
exec chroot $R /usr/bin/env \
    HOME=/root DISPLAY=:0 WAYLAND_DISPLAY=wayland-0 XDG_RUNTIME_DIR=/mnt/wslg/runtime-dir \
    GDK_BACKEND=${GDK_BACKEND:-x11} GSK_RENDERER=cairo LIBGL_ALWAYS_SOFTWARE=1 \
    WEBKIT_DISABLE_SANDBOX_THIS_IS_DANGEROUS=1 WEBKIT_DISABLE_DMABUF_RENDERER=1 \
    NO_AT_BRIDGE=1 GTK_A11Y=none LANG=C.UTF-8 \
    "$@"

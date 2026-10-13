#!/bin/bash
# Builds the XenonOS (Debian 13 + KDE) ISO.  Run as ROOT in WSL:   sudo bash build-iso.sh
#
# WARNING: This script downloads ~1.5-3 GB of Debian packages and installs live-build and debootstrap into WSL.
#         Get approval before running it.  Output: D:\XenonOS\debian\out\xenonos-*.iso
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
WORK=/root/xenonos-lb          # work on ext4 (permissions/device files break on a Windows drive)
OUT="$HERE/out"

if [ "$(id -u)" != 0 ]; then echo "run as root (sudo)"; exit 1; fi

echo ">> Installing required tools (apt)..."
apt-get update
apt-get install -y debootstrap debian-archive-keyring squashfs-tools xorriso grub-pc-bin grub-efi-amd64-bin mtools \
    syslinux syslinux-utils isolinux dosfstools python3 dpkg-dev librsvg2-bin
# live-build: needs Debian's current version (Ubuntu's 3.0~a57 package is too old for trixie)
if ! dpkg -l live-build 2>/dev/null | awk '/^ii/ {print $3}' | grep -qE '^1:20'; then
    bash "$HERE/get-live-build.sh"
fi

echo ">> Building XenonOS .deb packages..."
bash "$HERE/build-debs.sh"

echo ">> Preparing work directory: $WORK"
# unmount bind mounts left over from a previous attempt (so rm -rf does not touch them)
for m in $(awk -v p="$WORK/" 'index($2, p) == 1 { print $2 }' /proc/mounts | sort -r); do umount -l "$m" || true; done
rm -rf "$WORK"
mkdir -p "$WORK"
cp -a "$HERE/live-build/." "$WORK/"
chmod +x "$WORK"/auto/* "$WORK"/config/hooks/live/*.hook.chroot

# boot menu theme: copy live-build's templates and override the splash (XenonOS / Xe 54)
cp -a /usr/share/live/build/bootloaders "$WORK/config/bootloaders"
cp "$HERE/boot-splash.svg" "$WORK/config/bootloaders/splash.svg"

cd "$WORK"
echo ">> lb config"
lb clean --purge 2>/dev/null || true
lb config
echo ">> lb build (takes a long time: 20-60 min)"
lb build 2>&1 | tee "$HERE/build.log"

mkdir -p "$OUT"
ISO=$(ls -1 "$WORK"/*.iso | head -1)

# post-process: rename the boot menu entries (live-build hardcodes "Live system ...")
echo ">> boot menu labels -> XenonOS"
PP=$(mktemp -d)
for f in isolinux/live.cfg isolinux/menu.cfg isolinux/stdmenu.cfg isolinux/utilities.cfg boot/grub/grub.cfg boot/grub/config.cfg boot/grub/theme.cfg boot/grub/loopback.cfg; do
    mkdir -p "$PP/$(dirname "$f")"
    xorriso -osirrox on -indev "$ISO" -extract "/$f" "$PP/$f" >/dev/null 2>&1 || true
done
MAPS=()
for f in $(cd "$PP" && find . -type f | sed 's|^\./||'); do
    sed -i 's/Live system (amd64 fail-safe mode)/XenonOS Live (fail-safe mode)/; s/Live system (amd64)/XenonOS Live/; s/Live system/XenonOS Live/; s/Debian GNU\/Linux/XenonOS/g; s/menu title Boot menu/menu title XenonOS (Xe 54)/' "$PP/$f"
    MAPS+=(-map "$PP/$f" "/$f")
done
if [ ${#MAPS[@]} -gt 0 ]; then
    xorriso -indev "$ISO" -outdev "$ISO.new" "${MAPS[@]}" -boot_image any replay -commit >/dev/null 2>&1 \
        && mv "$ISO.new" "$ISO" && echo "   ${#MAPS[@]} files updated" || echo "   WARNING: could not update menu labels"
fi
rm -rf "$PP"
cp -v "$ISO" "$OUT/"
sha256sum "$OUT/$(basename "$ISO")" | tee "$OUT/SHA256SUMS"
echo ">> Ready: $OUT/$(basename "$ISO")"

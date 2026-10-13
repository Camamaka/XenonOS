#!/bin/bash
# XenonOS (Debian 13 + KDE) ISO'sunu uretir.  WSL'de ROOT olarak calistir:   sudo bash build-iso.sh
#
# DIKKAT: Bu betik internetten ~1.5-3 GB Debian paketi indirir ve WSL'e live-build, debootstrap kurar.
#         Calistirmadan once onay ver.  Cikti: D:\XenonOS\debian\out\xenonos-*.iso
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
WORK=/root/xenonos-lb          # ext4 uzerinde calis (Windows surucusunde izinler/aygit dosyalari bozulur)
OUT="$HERE/out"

if [ "$(id -u)" != 0 ]; then echo "root olarak calistir (sudo)"; exit 1; fi

echo ">> Gerekli araclar kuruluyor (apt)..."
apt-get update
apt-get install -y debootstrap debian-archive-keyring squashfs-tools xorriso grub-pc-bin grub-efi-amd64-bin mtools \
    syslinux syslinux-utils isolinux dosfstools python3 dpkg-dev librsvg2-bin
# live-build: Debian'in guncel surumu gerekir (Ubuntu'nun 3.0~a57 paketi trixie icin cok eski)
if ! dpkg -l live-build 2>/dev/null | awk '/^ii/ {print $3}' | grep -qE '^1:20'; then
    bash "$HERE/get-live-build.sh"
fi

echo ">> XenonOS .deb paketleri uretiliyor..."
bash "$HERE/build-debs.sh"

echo ">> Calisma klasoru hazirlaniyor: $WORK"
# onceki denemeden kalan bind mount'lari coz (rm -rf bunlara dokunmasin)
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
echo ">> lb build (uzun surer: 20-60 dk)"
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
        && mv "$ISO.new" "$ISO" && echo "   ${#MAPS[@]} dosya guncellendi" || echo "   UYARI: menu etiketleri guncellenemedi"
fi
rm -rf "$PP"
cp -v "$ISO" "$OUT/"
sha256sum "$OUT/$(basename "$ISO")" | tee "$OUT/SHA256SUMS"
echo ">> Hazir: $OUT/$(basename "$ISO")"

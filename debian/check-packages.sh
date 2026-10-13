#!/bin/bash
# Validates every name in the package list against the lb chroot's apt directory (no download)
CH=/root/xenonos-lb/chroot
LIST="$(cd "$(dirname "$0")" && pwd)/live-build/config/package-lists/xenonos.list.chroot"
[ -d "$CH/var/lib/apt/lists" ] || { echo "chroot apt listeleri yok"; exit 1; }
ls "$CH/var/lib/apt/lists" | head -3
missing=0
for p in $(grep -vE '^\s*(#|$)' "$LIST"); do
  case "$p" in xenonium|xenonpad|xenonwriter|xenonos-defaults) continue ;; esac
  if ! chroot "$CH" apt-cache show "$p" >/dev/null 2>&1; then
    echo "YOK: $p"
    # suggest similar ones
    chroot "$CH" apt-cache search --names-only "$(echo "$p" | sed 's/-.*//')" 2>/dev/null | head -4 | sed 's/^/    oneri: /'
    missing=1
  fi
done
[ $missing = 0 ] && echo "TUM PAKET ADLARI GECERLI"

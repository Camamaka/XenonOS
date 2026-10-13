#!/bin/bash
# Downloads and installs Debian's current live-build package (scripts only, ~200 KB) from deb.debian.org.
set -euo pipefail
POOL=https://deb.debian.org/debian/pool/main/l/live-build/
echo ">> surum araniyor: $POOL"
LIST=$(curl -fsSL "$POOL" | grep -oE 'live-build_[0-9][^"]*_all\.deb' | sort -uV)
echo "$LIST" | tail -5
FILE=$(echo "$LIST" | tail -1)
echo ">> indiriliyor: $FILE"
mkdir -p /root/lb-deb && cd /root/lb-deb
curl -fsSL -o "$FILE" "$POOL$FILE"
ls -la "$FILE"
apt-get install -y --allow-downgrades ./"$FILE"
dpkg -l live-build | tail -1 | awk '{print "kurulu: " $2, $3}'
lb config --help 2>&1 | grep -E 'bootloaders|--updates|image-name' | head

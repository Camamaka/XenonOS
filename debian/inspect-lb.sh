#!/bin/bash
echo "== version"; dpkg -l live-build | tail -1 | awk '{print $2, $3}'; lb --version 2>&1 | head -2
echo "== valid options"
lb config --help 2>&1 | grep -oE '^\s*--[a-z0-9-]+' | tr -d ' ' | sort -u | tr '\n' ' '
echo
echo "== lines about bootloader/updates/image-name"
lb config --help 2>&1 | grep -iE 'bootloader|updates|image-name|iso-|security|mode|apt-indices|memtest' | head -20
echo "== debian-installer / archive-areas"
lb config --help 2>&1 | grep -iE 'debian-installer|archive-areas|distribution' | head

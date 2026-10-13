#!/bin/bash
echo "== binary stage order (log)"
grep -nE '^\[20[0-9-]+ [0-9:]+\] lb (binary|chroot)_' /root/xenonos-iso-build.log | sed 's/^\([0-9]*\):\[[^]]*\]/\1:/' | cut -c1-80
echo "== xenonos boot hook line"
grep -n "xenonos\] boot menu" /root/xenonos-iso-build.log
echo "== text used to generate the live.cfg labels"
grep -n "Live system" /usr/lib/live/build/* 2>/dev/null | head -5 | cut -c1-160

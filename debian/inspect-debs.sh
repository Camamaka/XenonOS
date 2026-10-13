#!/bin/bash
cd "$(dirname "$0")/packages"
for p in xenonium xenonpad xenonwriter xenonos-defaults; do
  echo "=== $p"
  dpkg-deb -f ${p}_1.0_all.deb Package Version Architecture Depends
done
echo
echo "=== xenonium icerigi"
dpkg-deb -c xenonium_1.0_all.deb | awk '{print $1, $2, $6}' | head -24
echo
echo "=== xenonium postinst"
dpkg-deb -I xenonium_1.0_all.deb postinst | head -12
echo
echo "=== kurulum denemesi (gecici dizine acma)"
T=$(mktemp -d)
for p in xenonium xenonpad xenonwriter xenonos-defaults; do dpkg-deb -x ${p}_1.0_all.deb $T; done
ls $T/usr/bin $T/usr/share/applications
python3 -m py_compile $T/usr/lib/xenonos/xenonium/browser.py $T/usr/lib/xenonos/xenonpad/xenonpad.py $T/usr/lib/xenonos/xenonwriter/xenonwriter.py && echo "python derleme OK"
rm -rf $T

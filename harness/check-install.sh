#!/bin/bash
R=/root/work/rootfs
echo "== bin sarmalayicilar"; ls -la $R/usr/bin/xenonium $R/usr/bin/xenonpad $R/usr/bin/xenonwriter; cat $R/usr/bin/xenonium
echo "== uygulama dosyalari"; find $R/usr/lib/xenonos -type f | sed "s|$R||" | sort
echo "== desktop"; ls $R/usr/share/applications | grep -i xenon
echo "== simgeler"; ls -la $R/usr/share/icons/hicolor/scalable/apps/
echo "== alternatives"; ls -la $R/usr/bin/x-www-browser $R/etc/alternatives/x-www-browser
echo "== mimeapps"; grep -E 'http|text/plain|html' $R/etc/xdg/mimeapps.list
echo "== favorites"; grep favorite $R/etc/dconf/db/xenon.d/00-xenonos
echo "== brand servisi (firefox satiri olmamali)"; grep -n 'rn ' $R/usr/local/bin/xenon-brand
echo "== py derleme"; chroot $R python3 -m py_compile /usr/lib/xenonos/xenonium/browser.py /usr/lib/xenonos/xenonium/extensions.py /usr/lib/xenonos/xenonium/pages.py /usr/lib/xenonos/xenonium/store.py /usr/lib/xenonos/xenonpad/xenonpad.py /usr/lib/xenonos/xenonwriter/xenonwriter.py && echo "py_compile OK"
find $R/usr/lib/xenonos -name '__pycache__' -prune -exec rm -rf {} + 2>/dev/null; true

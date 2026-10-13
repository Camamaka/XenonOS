#!/bin/bash
# calisan test uygulamalarini kapat (chroot icindeki python/WebKit islemleri)
for p in $(pgrep -f 'usr/lib/xenonos|WebKitWebProcess|WebKitNetworkProcess|run-test.sh'); do
  [ "$p" != "$$" ] && kill "$p" 2>/dev/null
done
sleep 1
true

#!/bin/bash
# stop the running test apps (python/WebKit processes inside the chroot)
for p in $(pgrep -f 'usr/lib/xenonos|WebKitWebProcess|WebKitNetworkProcess|run-test.sh'); do
  [ "$p" != "$$" ] && kill "$p" 2>/dev/null
done
sleep 1
true

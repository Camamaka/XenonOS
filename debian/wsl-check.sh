#!/bin/bash
echo "cekirdek: $(nproc)"
free -m | awk '/Mem:/{print "ram_MB: " $2} /Swap:/{print "swap_MB: " $2}'
rm -rf /root/xenonos-lb && echo "yarim kalan derleme klasoru temizlendi"
df -h /root | tail -1 | awk '{print "bos alan: " $4}'

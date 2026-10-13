#!/bin/bash
echo "cpus: $(nproc)"
free -m | awk '/Mem:/{print "ram_MB: " $2} /Swap:/{print "swap_MB: " $2}'
rm -rf /root/xenonos-lb && echo "leftover half-finished build directory cleaned"
df -h /root | tail -1 | awk '{print "free space:" $4}'

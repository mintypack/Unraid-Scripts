#!/bin/bash

# Set CPU Governor to Ondemand
cpus=$(cat /proc/cpuinfo | grep processor | wc -l 2>/dev/null)
for ((i=0; i<${cpus}; ++i)); do
    /usr/bin/cpufreq-set -c $i -g 'ondemand' &>/dev/null
done

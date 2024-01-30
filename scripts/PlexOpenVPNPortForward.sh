#!/bin/bash

docker exec OpenVPN-Client iptables -t nat -I PREROUTING -p tcp --dport 44547 -j REDIRECT --to-ports 32400
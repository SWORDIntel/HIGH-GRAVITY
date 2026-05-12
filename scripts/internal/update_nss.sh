#!/bin/bash
echo "[*] Discovering NSS databases..."
find "$HOME" -name "cert9.db" | while read -r db; do
    dir=$(dirname "$db")
    echo "[*] Adding CA to $dir"
    certutil -d sql:"$dir" -A -t "CT,C,C" -n "HIGH-GRAVITY CA" -i certs/proxy.ca.crt 2>/dev/null
done
echo "[+] All NSS databases updated."

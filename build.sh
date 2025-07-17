#!/usr/bin/env bash
# Hentikan script jika ada perintah yang gagal
set -o errexit

# 1. Instal semua dependensi Python
pip install -r requirements.txt

# 2. Instal dependensi sistem untuk WeasyPrint
# Membersihkan cache apt terlebih dahulu untuk menghindari error
apt-get clean
apt-get update
apt-get install -y libpango-1.0-0 libpangoft2-1.0-0 libcairo2 libgdk-pixbuf-2.0-0
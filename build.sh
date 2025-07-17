#!/usr/bin/env bash
# Script ini akan dijalankan oleh Render saat proses build

# Hentikan script jika ada perintah yang gagal
set -o errexit

# 1. Instal semua dependensi Python dari requirements.txt
pip install -r requirements.txt

# 2. Instal dependensi sistem yang dibutuhkan oleh WeasyPrint
# Perintah ini menggunakan manajer paket apt-get (untuk sistem Debian/Ubuntu seperti Render)
apt-get update && apt-get install -y libpango-1.0-0 libpangoft2-1.0-0 libcairo2 libgdk-pixbuf-2.0-0
## file: server/pdf_generator.py (Lengkap & Final)

import os
from weasyprint import HTML
from flask import render_template
from datetime import datetime
import config

def format_rupiah(number):
    try:
        num = float(number)
        return f"{num:,.0f}".replace(",", ".")
    except (ValueError, TypeError):
        return "0"

def get_nama_lengkap_by_email(google_provider, email):
    if not email: return ""
    try:
        cabang_sheet = google_provider.sheet.worksheet(config.CABANG_SHEET_NAME)
        records = cabang_sheet.get_all_records()
        for record in records:
            if str(record.get('EMAIL_SAT', '')).strip().lower() == str(email).strip().lower():
                return record.get('NAMA LENGKAP', '').strip()
    except Exception as e:
        print(f"Error getting name for email {email}: {e}")
    return ""

def create_approval_details_block(google_provider, approver_email, approval_time_str):
    approver_name = get_nama_lengkap_by_email(google_provider, approver_email)
    try:
        approval_dt = datetime.fromisoformat(approval_time_str)
        formatted_time = approval_dt.strftime('%d %B %Y, %H:%M')
    except (ValueError, TypeError):
        formatted_time = "Waktu tidak tersedia"
    name_display = f"<strong>{approver_name}</strong><br>" if approver_name else ""
    return f"""
    <div class="approval-details">
        {name_display}
        {approver_email or ''}<br>
        Pada: {formatted_time}
    </div>
    """

def create_pdf_from_data(google_provider, form_data):
    grouped_items = {}
    grand_total = 0
    for i in range(1, 51):
        if form_data.get(f"Jenis_Pekerjaan_{i}"):
            kategori = form_data.get(f"Kategori_Pekerjaan_{i}", "Lain-lain")
            if kategori not in grouped_items: grouped_items[kategori] = []
            total_harga = float(form_data.get(f"Total_Harga_Item_{i}", 0))
            grand_total += total_harga
            item = {
                "jenisPekerjaan": form_data.get(f"Jenis_Pekerjaan_{i}"), "satuan": form_data.get(f"Satuan_Item_{i}"),
                "volume": float(form_data.get(f"Volume_Item_{i}", 0)), "hargaMaterial": format_rupiah(form_data.get(f"Harga_Material_Item_{i}", 0)),
                "hargaUpah": format_rupiah(form_data.get(f"Harga_Upah_Item_{i}", 0)), "totalMaterial": format_rupiah(form_data.get(f"Total_Material_Item_{i}", 0)),
                "totalUpah": format_rupiah(form_data.get(f"Total_Upah_Item_{i}", 0)), "totalHarga": format_rupiah(total_harga),
            }
            grouped_items[kategori].append(item)
    
    ppn = grand_total * 0.11
    final_grand_total = grand_total + ppn

    coordinator_approval_details = ""
    manager_approval_details = ""
    if form_data.get(config.COLUMN_NAMES.KOORDINATOR_APPROVER):
        coordinator_approval_details = create_approval_details_block(
            google_provider, form_data.get(config.COLUMN_NAMES.KOORDINATOR_APPROVER),
            form_data.get(config.COLUMN_NAMES.KOORDINATOR_APPROVAL_TIME)
        )
    if form_data.get(config.COLUMN_NAMES.MANAGER_APPROVER):
        manager_approval_details = create_approval_details_block(
            google_provider, form_data.get(config.COLUMN_NAMES.MANAGER_APPROVER),
            form_data.get(config.COLUMN_NAMES.MANAGER_APPROVAL_TIME)
        )
    
    # ▼▼▼ LOGIKA BARU UNTUK MEMFORMAT TANGGAL PENGAJUAN ▼▼▼
    tanggal_pengajuan_str = ''
    timestamp_from_data = form_data.get(config.COLUMN_NAMES.TIMESTAMP)
    if timestamp_from_data:
        try:
            # Coba format ISO (saat pertama kali submit dari Python)
            dt_object = datetime.fromisoformat(timestamp_from_data)
            tanggal_pengajuan_str = dt_object.strftime('%d %B %Y')
        except (ValueError, TypeError):
            # Jika gagal, coba format umum dari Google Sheets (misal: '7/3/2025 14:45:10')
            try:
                dt_object = datetime.strptime(timestamp_from_data, '%m/%d/%Y %H:%M:%S')
                tanggal_pengajuan_str = dt_object.strftime('%d %B %Y')
            except (ValueError, TypeError):
                # Jika masih gagal, tampilkan apa adanya (bagian tanggalnya saja)
                tanggal_pengajuan_str = str(timestamp_from_data).split(" ")[0]
            
    logo_path = 'file:///' + os.path.abspath(os.path.join('static', 'Alfamart-Emblem.png'))

    html_string = render_template(
        'pdf_report.html', data=form_data, grouped_items=grouped_items,
        grand_total=format_rupiah(grand_total), ppn=format_rupiah(ppn),
        final_grand_total=format_rupiah(final_grand_total), logo_path=logo_path,
        JABATAN=config.JABATAN,
        coordinator_approval_details=coordinator_approval_details,
        manager_approval_details=manager_approval_details,
        format_rupiah=format_rupiah,
        tanggal_pengajuan=tanggal_pengajuan_str # Kirim tanggal yang sudah diformat
    )
    
    return HTML(string=html_string).write_pdf()
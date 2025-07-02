import datetime
import os
import traceback
from flask import Flask, request, jsonify, render_template, url_for
from dotenv import load_dotenv
from flask_cors import CORS

import config
from google_services import GoogleServiceProvider
from pdf_generator import create_pdf_from_data

# Inisialisasi Aplikasi
load_dotenv()
app = Flask(__name__)
CORS(app)
google_provider = GoogleServiceProvider()

@app.route('/check_status', methods=['GET'])
def check_status():
    email = request.args.get('email')
    if not email:
        return jsonify({"error": "Email parameter is missing"}), 400
    try:
        status_data = google_provider.check_user_submissions(email)
        return jsonify(status_data), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/submit', methods=['POST'])
def submit_form():
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "Invalid JSON data"}), 400

    new_row_index = None
    try:
        data[config.COLUMN_NAMES.STATUS] = config.STATUS.WAITING_FOR_COORDINATOR
        data[config.COLUMN_NAMES.TIMESTAMP] = datetime.datetime.now().isoformat()
        
        new_row_index = google_provider.append_to_sheet(data, config.DATA_ENTRY_SHEET_NAME)
        
        try:
            cabang = data.get(config.COLUMN_NAMES.CABANG)
            coordinator_email = google_provider.get_email_by_jabatan(cabang, config.JABATAN.KOORDINATOR)
            if not coordinator_email:
                raise Exception(f"Coordinator email for branch {cabang} not found.")

            pdf_bytes = create_pdf_from_data(google_provider, data)
            proyek_name = data.get(config.COLUMN_NAMES.PROYEK, 'N_A')
            pdf_filename = f"RAB_{proyek_name}_{new_row_index}.pdf"
            base_url = request.url_root
            approval_url = f"{base_url}handle_approval?action=approve&row={new_row_index}&level=coordinator&approver={coordinator_email}"
            rejection_url = f"{base_url}handle_approval?action=reject&row={new_row_index}&level=coordinator&approver={coordinator_email}"
            email_html = render_template('email_template.html', level='Koordinator', form_data=data, approval_url=approval_url, rejection_url=rejection_url)
            
            google_provider.send_email(to=coordinator_email, subject=f"[TAHAP 1: PERLU PERSETUJUAN] RAB Proyek: {proyek_name}", html_body=email_html, pdf_attachment_bytes=pdf_bytes, pdf_filename=pdf_filename)
            
            return jsonify({"status": "success", "message": "Data successfully submitted and approval email sent."}), 200

        except Exception as email_error:
            if new_row_index:
                print(f"Email sending failed. Deleting row {new_row_index}...")
                google_provider.delete_row(config.DATA_ENTRY_SHEET_NAME, new_row_index)
            raise email_error

    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "error", "message": f"An error occurred: {str(e)}"}), 500

@app.route('/handle_approval', methods=['GET'])
def handle_approval():
    action = request.args.get('action')
    row_str = request.args.get('row')
    level = request.args.get('level')
    approver = request.args.get('approver')
    logo_url = url_for('static', filename='Alfamart-Emblem.png')

    if not all([action, row_str, level, approver]):
        return render_template('response_page.html', title='Incomplete Parameters', message='URL parameters are incomplete or invalid.', theme_color='#dc3545', icon='⚠️', logo_url=logo_url), 400
    try:
        row = int(row_str)
        row_data = google_provider.get_row_data(row)
        if not row_data:
            return render_template('response_page.html', title='Data Not Found', message='This request seems to be missing or has been deleted.', theme_color='#ffc107', icon='ⓘ', logo_url=logo_url)
        
        current_status = row_data.get(config.COLUMN_NAMES.STATUS, "").strip()
        expected_status_map = {'coordinator': config.STATUS.WAITING_FOR_COORDINATOR, 'manager': config.STATUS.WAITING_FOR_MANAGER}
        
        if current_status != expected_status_map.get(level):
            msg = f'This action has already been processed. Current status: <strong>{current_status}</strong>.'
            return render_template('response_page.html', title='Action Already Processed', message=msg, theme_color='#ffc107', icon='ⓘ', logo_url=logo_url)
        
        current_time = datetime.datetime.now().isoformat()
        cabang = row_data.get(config.COLUMN_NAMES.CABANG)
        proyek_name = row_data.get(config.COLUMN_NAMES.PROYEK, 'N_A')

        if level == 'coordinator':
            if action == 'approve':
                google_provider.update_cell(row, config.COLUMN_NAMES.STATUS, config.STATUS.WAITING_FOR_MANAGER)
                google_provider.update_cell(row, config.COLUMN_NAMES.KOORDINATOR_APPROVER, approver)
                google_provider.update_cell(row, config.COLUMN_NAMES.KOORDINATOR_APPROVAL_TIME, current_time)
                
                manager_email = google_provider.get_email_by_jabatan(cabang, config.JABATAN.MANAGER)
                if manager_email:
                    row_data[config.COLUMN_NAMES.KOORDINATOR_APPROVER] = approver
                    row_data[config.COLUMN_NAMES.KOORDINATOR_APPROVAL_TIME] = current_time
                    base_url = request.url_root
                    approval_url_manager = f"{base_url}handle_approval?action=approve&row={row}&level=manager&approver={manager_email}"
                    rejection_url_manager = f"{base_url}handle_approval?action=reject&row={row}&level=manager&approver={manager_email}"
                    email_html_manager = render_template('email_template.html', level='Manajer', form_data=row_data, approval_url=approval_url_manager, rejection_url=rejection_url_manager, additional_info=f"Telah disetujui oleh Koordinator: {approver}")
                    pdf_bytes = create_pdf_from_data(google_provider, row_data)
                    pdf_filename = f"RAB_{proyek_name}_{row}.pdf"
                    google_provider.send_email(manager_email, f"[TAHAP 2: PERLU PERSETUJUAN] RAB Proyek: {proyek_name}", email_html_manager, pdf_bytes, pdf_filename)
                
                return render_template('response_page.html', title='Persetujuan Diteruskan', message='Terima kasih. Persetujuan Anda telah dicatat dan permintaan diteruskan ke Manajer.', theme_color='#28a745', icon='✔', logo_url=logo_url)

            elif action == 'reject':
                google_provider.update_cell(row, config.COLUMN_NAMES.STATUS, config.STATUS.REJECTED_BY_COORDINATOR)
                google_provider.update_cell(row, config.COLUMN_NAMES.KOORDINATOR_APPROVER, approver)
                google_provider.update_cell(row, config.COLUMN_NAMES.KOORDINATOR_APPROVAL_TIME, current_time)
                return render_template('response_page.html', title='Permintaan Ditolak', message='Status permintaan telah diperbarui menjadi ditolak.', theme_color='#dc3545', icon='✖', logo_url=logo_url)
        
        elif level == 'manager':
            if action == 'approve':
                google_provider.update_cell(row, config.COLUMN_NAMES.STATUS, config.STATUS.APPROVED)
                google_provider.update_cell(row, config.COLUMN_NAMES.MANAGER_APPROVER, approver)
                google_provider.update_cell(row, config.COLUMN_NAMES.MANAGER_APPROVAL_TIME, current_time)

                # ▼▼▼ LOGIKA EMAIL FINAL DITAMBAHKAN DI SINI ▼▼▼
                # 1. Dapatkan semua email penerima
                support_email = google_provider.get_email_by_jabatan(cabang, config.JABATAN.SUPPORT)
                manager_email = approver # Manager yang menyetujui
                coordinator_email = row_data.get(config.COLUMN_NAMES.KOORDINATOR_APPROVER)
                
                if support_email:
                    # 2. Siapkan daftar CC
                    cc_list = [manager_email, coordinator_email]
                    # Hapus duplikat atau nilai kosong dari daftar CC
                    cc_list = list(filter(None, set(cc_list)))
                    
                    # 3. Siapkan data terbaru untuk PDF
                    row_data[config.COLUMN_NAMES.STATUS] = config.STATUS.APPROVED
                    row_data[config.COLUMN_NAMES.MANAGER_APPROVER] = approver
                    row_data[config.COLUMN_NAMES.MANAGER_APPROVAL_TIME] = current_time

                    # 4. Buat email dan PDF
                    subject = f"[FINAL - DISETUJUI] Pengajuan RAB Proyek: {proyek_name}"
                    email_body_html = f"<p>Pengajuan RAB untuk proyek <b>{proyek_name}</b> di cabang <b>{cabang}</b> telah disetujui sepenuhnya.</p><p>Dokumen final terlampir untuk arsip.</p>"
                    pdf_bytes = create_pdf_from_data(google_provider, row_data)
                    pdf_filename = f"RAB_{proyek_name}_FINAL.pdf"
                    
                    # 5. Kirim email
                    google_provider.send_email(
                        to=support_email,
                        cc=cc_list,
                        subject=subject,
                        html_body=email_body_html,
                        pdf_attachment_bytes=pdf_bytes,
                        pdf_filename=pdf_filename
                    )
                
                return render_template('response_page.html', title='Persetujuan Berhasil', message='Tindakan Anda telah berhasil diproses dan notifikasi final telah dikirim.', theme_color='#28a745', icon='✔', logo_url=logo_url)

            elif action == 'reject':
                google_provider.update_cell(row, config.COLUMN_NAMES.STATUS, config.STATUS.REJECTED_BY_MANAGER)
                google_provider.update_cell(row, config.COLUMN_NAMES.MANAGER_APPROVER, approver)
                google_provider.update_cell(row, config.COLUMN_NAMES.MANAGER_APPROVAL_TIME, current_time)
                return render_template('response_page.html', title='Permintaan Ditolak', message='Status permintaan telah diperbarui menjadi ditolak.', theme_color='#dc3545', icon='✖', logo_url=logo_url)

    except Exception as e:
        traceback.print_exc()
        return render_template('response_page.html', title='Internal Error', message=f'An internal error occurred.<br><small>Details: {e}</small>', theme_color='#dc3545', icon='⚠️', logo_url=logo_url), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
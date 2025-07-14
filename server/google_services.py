import os.path
import io
import gspread
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime, timezone

import config

class GoogleServiceProvider:
    def __init__(self):
        self.scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/gmail.send',
            'https://www.googleapis.com/auth/drive.file'
        ]
        self.creds = None
        
        secret_dir = '/etc/secrets/'
        token_path = os.path.join(secret_dir, 'token.json')
        client_secret_path = os.path.join(secret_dir, 'client_secret.json')

        if not os.path.exists(secret_dir):
            token_path = 'token.json'
            client_secret_path = 'client_secret.json'

        if os.path.exists(token_path):
            self.creds = Credentials.from_authorized_user_file(token_path, self.scopes)
        
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(client_secret_path, self.scopes)
                self.creds = flow.run_local_server(port=0)
            
            with open(token_path, 'w') as token:
                token.write(self.creds.to_json())

        self.gspread_client = gspread.authorize(self.creds)
        self.sheet = self.gspread_client.open_by_key(config.SPREADSHEET_ID)
        self.data_entry_sheet = self.sheet.worksheet(config.DATA_ENTRY_SHEET_NAME)
        self.gmail_service = build('gmail', 'v1', credentials=self.creds)
        self.drive_service = build('drive', 'v3', credentials=self.creds)

    def upload_pdf_to_drive(self, pdf_bytes, filename):
        file_metadata = {'name': filename, 'parents': [config.PDF_STORAGE_FOLDER_ID]}
        media = MediaIoBaseUpload(io.BytesIO(pdf_bytes), mimetype='application/pdf')
        file = self.drive_service.files().create(body=file_metadata, media_body=media, fields='id, webViewLink').execute()
        self.drive_service.permissions().create(fileId=file.get('id'), body={'type': 'anyone', 'role': 'reader'}).execute()
        return file.get('webViewLink')

    # ▼▼▼ LOGIKA PENCARIAN RIWAYAT DIPERBARUI TOTAL ▼▼▼
    def check_user_submissions(self, email):
        try:
            all_values = self.data_entry_sheet.get_all_values()
            if len(all_values) <= 1:
                return {"active_codes": {"pending": [], "approved": []}, "rejected_submissions": []}

            headers = all_values[0]
            records = [dict(zip(headers, row)) for row in all_values[1:]]
            
            global_pending_codes = []
            global_approved_codes = []
            user_rejected_submissions = []
            
            processed_locations_for_status = set()
            
            # Iterasi dari baru ke lama untuk menentukan status final setiap kode toko
            for record in reversed(records):
                lokasi = str(record.get(config.COLUMN_NAMES.LOKASI, "")).strip()
                if not lokasi or lokasi in processed_locations_for_status:
                    continue
                
                status = str(record.get(config.COLUMN_NAMES.STATUS, "")).strip()
                
                if status in [config.STATUS.WAITING_FOR_COORDINATOR, config.STATUS.WAITING_FOR_MANAGER]:
                    global_pending_codes.append(lokasi)
                    processed_locations_for_status.add(lokasi)
                elif status == config.STATUS.APPROVED:
                    global_approved_codes.append(lokasi)
                    processed_locations_for_status.add(lokasi)
                elif str(record.get(config.COLUMN_NAMES.EMAIL_PEMBUAT, "")).strip() == email and \
                     status in [config.STATUS.REJECTED_BY_COORDINATOR, config.STATUS.REJECTED_BY_MANAGER]:
                    user_rejected_submissions.append({key.replace(' ', '_'): val for key, val in record.items()})
                    processed_locations_for_status.add(lokasi)

            return {
                "active_codes": {
                    "pending": global_pending_codes,
                    "approved": global_approved_codes
                },
                "rejected_submissions": user_rejected_submissions
            }
        except Exception as e:
            raise e

    def get_sheet_headers(self, worksheet_name):
        return self.sheet.worksheet(worksheet_name).row_values(1)

    def append_to_sheet(self, data, worksheet_name):
        worksheet = self.sheet.worksheet(worksheet_name)
        headers = self.get_sheet_headers(worksheet_name)
        row_data = [data.get(header, "") for header in headers]
        worksheet.append_row(row_data)
        return len(worksheet.get_all_values())

    def get_row_data(self, row_index):
        records = self.data_entry_sheet.get_all_records()
        if row_index > 1 and row_index <= len(records) + 1:
            return records[row_index - 2]
        return {}

    def update_cell(self, row_index, column_name, value):
        try:
            col_index = self.data_entry_sheet.row_values(1).index(column_name) + 1
            self.data_entry_sheet.update_cell(row_index, col_index, value)
            return True
        except Exception as e:
            print(f"Error updating cell [{row_index}, {column_name}]: {e}")
            return False

    def get_email_by_jabatan(self, branch_name, jabatan):
        try:
            cabang_sheet = self.sheet.worksheet(config.CABANG_SHEET_NAME)
            for record in cabang_sheet.get_all_records():
                sheet_branch = str(record.get('CABANG', '')).strip().lower()
                input_branch = str(branch_name).strip().lower()
                sheet_jabatan = str(record.get('JABATAN', '')).strip().upper()
                input_jabatan = str(jabatan).strip().upper()
                if sheet_branch == input_branch and sheet_jabatan == input_jabatan:
                    return record.get('EMAIL_SAT')
        except gspread.exceptions.WorksheetNotFound:
            print(f"Error: Worksheet '{config.CABANG_SHEET_NAME}' not found.")
        return None

    def send_email(self, to, subject, html_body, pdf_attachment_bytes=None, pdf_filename="RAB.pdf", cc=None):
        try:
            message = MIMEMultipart()
            message['to'] = to; message['subject'] = subject
            if cc: message['cc'] = ', '.join(cc)
            message.attach(MIMEText(html_body, 'html'))
            if pdf_attachment_bytes:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(pdf_attachment_bytes)
                encoders.encode_base64(part)
                part.add_header('Content-Disposition', f'attachment; filename="{pdf_filename}"')
                message.attach(part)
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            create_message = {'raw': raw_message}
            send_message = self.gmail_service.users().messages().send(userId='me', body=create_message).execute()
            print(f"Email sent successfully to {to}. Message ID: {send_message['id']}")
            return send_message
        except Exception as e:
            print(f"An error occurred while sending email: {e}")
            raise e
    
    def copy_to_approved_sheet(self, row_data):
        try:
            approved_sheet = self.sheet.worksheet(config.APPROVED_DATA_SHEET_NAME)
            headers = self.get_sheet_headers(config.APPROVED_DATA_SHEET_NAME)
            data_to_append = [row_data.get(header, "") for header in headers]
            approved_sheet.append_row(data_to_append)
            print(f"Data successfully copied to {config.APPROVED_DATA_SHEET_NAME}.")
            return True
        except Exception as e:
            print(f"Failed to copy data to approved sheet: {e}")
            return False

    def delete_row(self, worksheet_name, row_index):
        try:
            worksheet = self.sheet.worksheet(worksheet_name)
            worksheet.delete_rows(row_index)
            print(f"Successfully deleted row {row_index} from {worksheet_name}.")
            return True
        except Exception as e:
            print(f"Failed to delete row {row_index} from {worksheet_name}: {e}")
            return False
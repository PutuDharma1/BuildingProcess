import os
from dotenv import load_dotenv

load_dotenv()

# --- Google & Spreadsheet Configuration ---
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID", "1LA1TlhgltT2bqSN3H-LYasq9PtInVlqq98VPru8txoo")
PDF_STORAGE_FOLDER_ID = "1fyIieJwLm4ZFoKZ0J5fOChp6gIC3NmrV" # ID Folder Google Drive Anda

# Nama-nama sheet yang digunakan
DATA_ENTRY_SHEET_NAME = "Form2"
APPROVED_DATA_SHEET_NAME = "Form3"
CABANG_SHEET_NAME = "Cabang"

# --- Column Name Constants ---
class COLUMN_NAMES:
    STATUS = "Status"
    TIMESTAMP = "Timestamp"
    EMAIL_PEMBUAT = "Email_Pembuat"
    LOKASI = "Lokasi"
    PROYEK = "Proyek"
    CABANG = "Cabang"
    KOORDINATOR_APPROVER = "Persetujuan Koordinator"
    KOORDINATOR_APPROVAL_TIME = "Waktu Persetujuan Koordinator"
    MANAGER_APPROVER = "Pemberi Persetujuan Manager"
    MANAGER_APPROVAL_TIME = "Waktu Persetujuan Manager"
    LINK_PDF = "Link PDF"

# --- Role & Status Constants ---
class JABATAN:
    SUPPORT = "BRANCH BUILDING SUPPORT"
    KOORDINATOR = "BRANCH BUILDING COORDINATOR"
    MANAGER = "BRANCH BUILDING & MAINTENANCE MANAGER"

class STATUS:
    WAITING_FOR_COORDINATOR = "Menunggu Persetujuan Koordinator"
    REJECTED_BY_COORDINATOR = "Ditolak oleh Koordinator"
    WAITING_FOR_MANAGER = "Menunggu Persetujuan Manajer"
    REJECTED_BY_MANAGER = "Ditolak oleh Manajer"
    APPROVED = "Disetujui"
import os
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow


# 權限範圍，只需 Drive 基本存取
SCOPES = ['https://www.googleapis.com/auth/drive.file']

# Step 1: 驗證授權
def get_credentials():
    creds_file_path = "./config/google-drive-api-credentials.json"
    creds = service_account.Credentials.from_service_account_file(
        creds_file_path, scopes=SCOPES
    )
    return creds

# Step 2: 上傳檔案到指定資料夾
def upload_file_to_drive(file_path, folder_id):
    creds = get_credentials()
    service = build('drive', 'v3', credentials=creds)

    file_metadata = {
        'name': os.path.basename(file_path),
        'parents': [folder_id]  # 指定目標資料夾 ID
    }
    media = MediaFileUpload(file_path, resumable=True)
    file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    print(f"Uploaded file ID: {file.get('id')}")
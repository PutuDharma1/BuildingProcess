import os
from google_auth_oauthlib.flow import InstalledAppFlow

# The scopes must match exactly what's in your main application
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/drive.file'
]

CLIENT_SECRET_FILE = 'client_secret.json'
TOKEN_FILE = 'token.json'

def generate_token():
    """Generates a new token.json file through local authentication."""
    if os.path.exists(TOKEN_FILE):
        print(f"'{TOKEN_FILE}' already exists. Please delete or rename it and run again.")
        return

    if not os.path.exists(CLIENT_SECRET_FILE):
        print(f"Error: '{CLIENT_SECRET_FILE}' not found in this directory.")
        return

    try:
        flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
        # This will open a browser window for you to log in
        creds = flow.run_local_server(port=0)

        # Save the new credentials for the server to use
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
        
        print(f"\nSuccess! A new '{TOKEN_FILE}' has been created.")
        print("Please upload this file to your server (e.g., Render's Secret Files).")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == '__main__':
    generate_token()
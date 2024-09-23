import base64
import json
import os

from fastapi import FastAPI, Request, HTTPException
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# FastAPI app
app = FastAPI()

# OAuth 2.0 scopes
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

# Path to credentials.json and token.json
CREDENTIALS_FILE = 'credentials.json'
TOKEN_FILE = 'token.json'


# Gmail API authentication
def get_gmail_service():
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(GoogleRequest())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for future use
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())

    service = build('gmail', 'v1', credentials=creds)
    return service


# Extract email message details
def get_message(service, user_id, message_id):
    message = service.users().messages().get(userId=user_id, id=message_id).execute()
    return message


# Reply to an email
def reply_to_email(service, user_id, message_id, message_body):
    original_message = service.users().messages().get(userId=user_id, id=message_id, format='full').execute()
    headers = original_message['payload']['headers']

    subject = ''
    from_email = ''
    for header in headers:
        if header['name'] == 'Subject':
            subject = header['value']
        if header['name'] == 'From':
            from_email = header['value']

    # Create the reply
    reply_message = {
        'raw': base64.urlsafe_b64encode(f"""\
        To: {from_email}
        Subject: Re: {subject}
        In-Reply-To: {original_message['id']}
        References: {original_message['id']} {message_body}""".encode('utf-8')).decode('utf-8')
    }

    # Send the reply
    sent_message = service.users().messages().send(userId=user_id, body=reply_message).execute()
    return sent_message


# Endpoint to handle Pub/Sub notifications
@app.post("/gmail/webhook/")
async def handle_gmail_notification(request: Request):
    try:
        # Parse the Pub/Sub message
        body = await request.json()

        # Decode the base64-encoded Pub/Sub message
        message_data = body['message']['data']
        message_json = json.loads(base64.b64decode(message_data).decode('utf-8'))

        email_address = message_json.get('emailAddress')
        history_id = message_json.get('historyId')

        if not email_address or not history_id:
            raise HTTPException(status_code=400, detail="Invalid Gmail notification format")

        # Initialize Gmail service
        service = get_gmail_service()

        # Fetch the most recent message from Gmail using historyId
        history = service.users().history().list(userId='me', startHistoryId=history_id).execute()
        if 'history' in history:
            for record in history['history']:
                if 'messagesAdded' in record:
                    for message in record['messagesAdded']:
                        message_id = message['message']['id']

                        # Get the full message details
                        email_message = get_message(service, 'me', message_id)
                        print(f"New email: {email_message['snippet']}")

                        # Reply to the email
                        reply_message_body = "Thank you for your email. We will get back to you soon."
                        reply = reply_to_email(service, 'me', message_id, reply_message_body)
                        print(f"Reply sent: {reply}")

        return {"status": "success"}

    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Demo GET endpoint
@app.get("/")
async def root():
    return {"message": "Hello, World!"}
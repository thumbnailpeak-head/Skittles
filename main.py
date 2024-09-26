import base64
import json
import os

from fastapi import FastAPI, Request, HTTPException
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from src.llm.chatgpt import chat_with_gpt4
from fastapi.middleware.cors import CORSMiddleware

import src.input.text.text_endpoint
import src.use_cases.chat_bot
import src.use_cases.voice_bot
from fastapi.staticfiles import StaticFiles
from pathlib import Path


# FastAPI app
app = FastAPI()
app.include_router(src.input.text.text_endpoint.router, prefix="/pdfs", tags=["pdfs"])
app.include_router(src.use_cases.chat_bot.router, prefix="/chatbot", tags=["chatbot"])
app.include_router(src.use_cases.voice_bot.router, prefix="/voicebot", tags=["voicebot"])
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this for production, e.g., ["http://localhost:3000"]
    allow_methods=["*"],
    allow_headers=["*"],
)
current_directory = Path(__file__).parent

# Define the relative path to the static folder
static_directory = current_directory / "static"

app.mount("/", StaticFiles(directory=static_directory, html=True), name="static")

# OAuth 2.0 scopes
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']


# Need to configure offline
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
                        if email_message:
                            print("Email fetched successfully.")

                            # Step 3: Extract the email body content
                            email_content = get_email_body(email_message)
                            if email_content:
                                print(f"Email content: {email_content}")

                                # Step 4: Generate a reply using GPT-4
                                gpt_reply = chat_with_gpt4(f"Here is an email I received:\n\n{email_content}\n\nWrite a polite, professional reply.")
                                if gpt_reply:
                                    print(f"Generated GPT-4 reply: {gpt_reply}")

                                    # Step 5: Reply to the email
                                    reply_to_email(service, "me", email_message['id'], gpt_reply, email_message)
                                else:
                                    print("Failed to generate GPT-4 reply.")
                            else:
                                print("No valid email body found.")

        return {"status": "success"}

    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Demo GET endpoint
@app.get("/")
async def root():
    return {"message": "Hello, World!"}


def get_email_body(message):
    """Extract the plain text body from the email message."""
    try:
        parts = message['payload'].get('parts', [])
        for part in parts:
            if part['mimeType'] == 'text/plain':
                body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                return body
        return None
    except Exception as e:
        print(f"Error in getting email body: {e}")
        return None

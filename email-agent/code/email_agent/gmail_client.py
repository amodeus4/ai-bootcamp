"""Gmail authentication and email fetching."""

import os
import pickle
import re
from typing import Dict, List
from datetime import datetime
from email.utils import parsedate_to_datetime
import base64

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from .schemas import EmailDocument, EmailAttachment
from .attachments import AttachmentManager

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
]


def authenticate_gmail(
    credentials_file: str = "credentials.json", token_file: str = "token.pickle"
) -> object:
    """Authenticate and return Gmail API service."""
    creds = None

    # Load existing credentials
    if os.path.exists(token_file):
        with open(token_file, "rb") as token:
            creds = pickle.load(token)

    # If no valid credentials, let user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
            creds = flow.run_local_server(port=0)

        # Save credentials for next run
        with open(token_file, "wb") as token:
            pickle.dump(creds, token)

    return build("gmail", "v1", credentials=creds)


class EmailDocumentParser:
    """Converts Gmail API responses into EmailDocument objects."""

    def __init__(self, gmail_service, attachment_manager: AttachmentManager = None):
        self.service = gmail_service
        self.attachment_manager = attachment_manager or AttachmentManager()

    def parse_email(self, email_data: Dict) -> EmailDocument:
        """Parse Gmail API response into EmailDocument."""

        headers = {
            h["name"].lower(): h["value"] for h in email_data["payload"]["headers"]
        }

        sender_full = headers.get("from", "")
        sender_name, sender_email = self._parse_email_address(sender_full)

        recipients = self._parse_recipients(headers.get("to", ""))

        date_str = headers.get("date", "")
        email_date = self._parse_date(date_str)

        body_plain = self._extract_body(email_data["payload"])

        labels = email_data.get("labelIds", [])
        is_read = "UNREAD" not in labels

        # Extract and process attachments
        attachments = []
        has_attachments = False

        if "parts" in email_data["payload"]:
            attachments_info = self._extract_attachments_info(
                email_data["payload"]["parts"]
            )
            if attachments_info:
                has_attachments = True
                # Process each attachment
                processed = self.attachment_manager.process_email_attachments(
                    self.service, email_data["id"], attachments_info
                )

                # Convert processed data to EmailAttachment objects
                for att_data in processed.get("attachments", []):
                    attachment = EmailAttachment(
                        filename=att_data["filename"],
                        mime_type=att_data.get("mime_type", ""),
                        attachment_id="",  # Already downloaded
                        size=0,
                        parsed_content=att_data.get("content"),
                        file_path=att_data.get("file_path"),
                    )
                    attachments.append(attachment)

        return EmailDocument(
            email_id=email_data["id"],
            thread_id=email_data["threadId"],
            sender_name=sender_name,
            sender_email=sender_email,
            recipients=recipients,
            subject=headers.get("subject", "(No Subject)"),
            date=email_date,
            body_plain=body_plain,
            snippet=email_data.get("snippet", ""),
            labels=labels,
            is_read=is_read,
            attachments=attachments,
            has_attachments=has_attachments,
            processing_status="pending",
        )

    @staticmethod
    def _parse_email_address(address: str) -> tuple:
        """Parse 'Name <email@example.com>' format."""
        match = re.match(r"(.+?)\s*<(.+?)>", address)
        if match:
            return match.group(1).strip('"'), match.group(2)
        return address, address

    @staticmethod
    def _parse_recipients(recipients_str: str) -> List[str]:
        """Parse comma-separated recipients."""
        if not recipients_str:
            return []
        return [r.strip() for r in recipients_str.split(",")]

    @staticmethod
    def _parse_date(date_str: str) -> datetime:
        """Parse email date string."""
        try:
            return parsedate_to_datetime(date_str)
        except Exception:
            return datetime.now()

    @staticmethod
    def _extract_body(payload: Dict) -> str:
        """Extract plain text body."""
        if "parts" in payload:
            for part in payload["parts"]:
                if part.get("mimeType") == "text/plain":
                    data = part["body"].get("data", "")
                    if data:
                        return base64.urlsafe_b64decode(data).decode(
                            "utf-8", errors="ignore"
                        )
        else:
            data = payload["body"].get("data", "")
            if data:
                return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
        return ""

    @staticmethod
    def _extract_attachments_info(parts: List[Dict]) -> List[Dict]:
        """Extract attachment information from email parts."""
        attachments = []
        for part in parts:
            if part.get("filename"):
                attachments.append(
                    {
                        "filename": part.get("filename", "unknown"),
                        "mimeType": part.get("mimeType", "application/octet-stream"),
                        "attachmentId": part.get("body", {}).get("attachmentId", ""),
                    }
                )
        return attachments


def fetch_and_index_all_emails(
    service, es_store, max_emails: int = 50
) -> List[EmailDocument]:
    """Fetch emails from Gmail and index them."""

    parser = EmailDocumentParser(service)

    results = (
        service.users().messages().list(userId="me", maxResults=max_emails).execute()
    )

    messages = results.get("messages", [])
    documents = []

    print(f"\n📧 Fetching {len(messages)} emails...")

    for i, msg in enumerate(messages, 1):
        try:
            email_data = (
                service.users()
                .messages()
                .get(userId="me", id=msg["id"], format="full")
                .execute()
            )

            doc = parser.parse_email(email_data)
            documents.append(doc)

            if i % 10 == 0:
                print(f"  Processed {i}/{len(messages)}...")

        except Exception as e:
            print(f" Error processing email {msg['id']}: {e}")

    print(f"✓ Indexing {len(documents)} emails to Elasticsearch...")
    result = es_store.bulk_index(documents)

    print(f"✓ Successfully indexed {result['success']} emails")
    if result["failed"]:
        print(f"Failed to index {result['failed']} emails")

    return documents

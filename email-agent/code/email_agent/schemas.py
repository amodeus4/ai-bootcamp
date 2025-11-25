"""Email data models and schemas."""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime


@dataclass
class EmailAttachment:
    """Represents an email attachment."""

    filename: str
    mime_type: str
    attachment_id: str
    size: int
    content: Optional[bytes] = None
    parsed_content: Optional[str] = None  # Markitdown-parsed content
    file_path: Optional[str] = None  # Path to saved file on disk

    def to_es_dict(self) -> Dict:
        """Convert to Elasticsearch-friendly format."""
        return {
            "filename": self.filename,
            "mime_type": self.mime_type,
            "size": self.size,
            "has_content": self.content is not None,
            "has_parsed_content": self.parsed_content is not None,
            "parsed_content": self.parsed_content[:2000]
            if self.parsed_content
            else None,  # Store preview
        }


@dataclass
class EmailDocument:
    """Elasticsearch-optimized email document structure."""

    # Required fields
    email_id: str
    thread_id: str
    sender_name: str
    sender_email: str
    subject: str

    # Optional fields with defaults
    recipients: List[str] = field(default_factory=list)
    cc: List[str] = field(default_factory=list)
    bcc: List[str] = field(default_factory=list)
    body_plain: str = ""
    body_html: str = ""
    snippet: str = ""
    date: datetime = field(default_factory=datetime.now)
    processed_at: Optional[datetime] = None
    attachments: List[EmailAttachment] = field(default_factory=list)
    labels: List[str] = field(default_factory=list)
    category: Optional[str] = None
    priority: str = "normal"
    is_read: bool = False
    is_important: bool = False
    is_starred: bool = False
    has_attachments: bool = False
    extracted_data: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None
    action_items: List[Dict[str, Any]] = field(default_factory=list)
    processing_status: str = "pending"
    processing_errors: List[str] = field(default_factory=list)
    thread_messages_count: int = 1
    is_thread_starter: bool = False

    def to_es_document(self) -> Dict:
        """Convert to Elasticsearch document format."""
        return {
            "_id": self.email_id,
            "_source": {
                "email_id": self.email_id,
                "thread_id": self.thread_id,
                "sender": {"name": self.sender_name, "email": self.sender_email},
                "recipients": self.recipients,
                "cc": self.cc,
                "bcc": self.bcc,
                "subject": self.subject,
                "body": {"plain": self.body_plain, "html": self.body_html},
                "snippet": self.snippet,
                "date": self.date.isoformat(),
                "processed_at": self.processed_at.isoformat()
                if self.processed_at
                else None,
                "attachments": [att.to_es_dict() for att in self.attachments],
                "has_attachments": len(self.attachments) > 0,
                "attachment_count": len(self.attachments),
                "labels": self.labels,
                "category": self.category,
                "priority": self.priority,
                "is_read": self.is_read,
                "is_important": self.is_important,
                "is_starred": self.is_starred,
                "extracted_data": self.extracted_data,
                "action_items": self.action_items,
                "action_count": len(self.action_items),
                "processing_status": self.processing_status,
                "processing_errors": self.processing_errors,
                "embedding": self.embedding,
                "thread_messages_count": self.thread_messages_count,
                "is_thread_starter": self.is_thread_starter,
            },
        }

    def get_context_for_llm(
        self,
        include_body: bool = True,
        max_body_length: int = 1000,
        include_attachments: bool = True,
    ) -> str:
        """Get formatted context for LLM."""
        body = self.body_plain[:max_body_length] if include_body else self.snippet
        if len(self.body_plain) > max_body_length and include_body:
            body += "\n[... truncated ...]"

        context = f"""
Subject: {self.subject}
From: {self.sender_name} <{self.sender_email}>
Date: {self.date.strftime("%Y-%m-%d %H:%M")}
Body: {body}
Attachments: {len(self.attachments)} file(s)
        """.strip()

        # Include parsed attachment content if requested
        if include_attachments and self.attachments:
            attachment_content = []
            for att in self.attachments:
                if att.parsed_content:
                    attachment_content.append(
                        f"\n--- Attachment: {att.filename} ---\n{att.parsed_content[:1000]}"
                    )

            if attachment_content:
                context += "\n\n## Attachment Content:\n" + "\n".join(
                    attachment_content
                )

        return context


@dataclass
class EmailThread:
    """Represents an email thread with multiple messages."""

    thread_id: str
    subject: str
    participants: List[Dict[str, str]] = field(default_factory=list)
    messages: List[EmailDocument] = field(default_factory=list)
    last_message_date: datetime = field(default_factory=datetime.now)
    message_count: int = 0

    def get_summary(self) -> str:
        """Get a summary of the thread."""
        if not self.messages:
            return "Empty thread"

        msg_count = len(self.messages)
        participant_list = ", ".join(
            [p.get("name", p.get("email", "Unknown")) for p in self.participants]
        )
        first_msg = self.messages[0]

        return f"Thread: {self.subject} ({msg_count} messages) with {participant_list}, started {first_msg.date.strftime('%Y-%m-%d')}"

    def get_full_conversation(self) -> str:
        """Get the full thread conversation."""
        conversation = f"=== Thread: {self.subject} ===\n\n"
        for i, msg in enumerate(self.messages, 1):
            conversation += f"[Message {i}] From: {msg.sender_name} <{msg.sender_email}> ({msg.date.strftime('%Y-%m-%d %H:%M')})\n"
            conversation += f"{msg.body_plain}\n\n"
            conversation += "-" * 50 + "\n\n"
        return conversation

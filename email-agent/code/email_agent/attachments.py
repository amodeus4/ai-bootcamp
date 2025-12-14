"""Attachment handling and document parsing with markitdown."""

import base64
import re
from typing import Dict, List, Optional
from pathlib import Path
from datetime import datetime

try:
    import markitdown
except ImportError:
    markitdown = None


# MIME types to skip (images used in signatures, inline graphics, etc.)
SKIP_ATTACHMENT_MIMES = {
    "image/gif",
    "image/x-icon",
    "image/bmp",
}

# Filename patterns to skip (common signature/logo filenames)
SKIP_ATTACHMENT_PATTERNS = [
    r"^image\d*\.",  # image001.png, image.gif
    r"^logo",  # logo.png, logo-company.jpg
    r"^signature",  # signature.png
    r"^icon",  # icon.png
    r"^banner",  # banner.jpg
    r"^footer",  # footer.png
    r"^header",  # header.jpg
    r"_signature\.",  # company_signature.png
    r"_logo\.",  # company_logo.png
]


def is_relevant_attachment(filename: str, mime_type: str) -> bool:
    """Check if an attachment is relevant (not a signature/logo/inline image)."""
    if not filename:
        return False

    filename_lower = filename.lower()

    # Skip certain MIME types entirely
    if mime_type in SKIP_ATTACHMENT_MIMES:
        return False

    # Skip small inline images (likely signatures)
    for pattern in SKIP_ATTACHMENT_PATTERNS:
        if re.match(pattern, filename_lower):
            return False

    # Relevant document extensions - always include
    relevant_extensions = {
        ".pdf",
        ".doc",
        ".docx",
        ".xls",
        ".xlsx",
        ".csv",
        ".txt",
        ".ppt",
        ".pptx",
        ".rtf",
        ".odt",
        ".ods",
        ".zip",
        ".rar",
    }

    ext = "." + filename_lower.rsplit(".", 1)[-1] if "." in filename_lower else ""

    # If it has a relevant extension, always include
    if ext in relevant_extensions:
        return True

    # For images, only include if they look like actual attachments (not inline)
    if mime_type.startswith("image/"):
        # Skip if filename is very short or generic
        if len(filename_lower) < 10:
            return False
        # Include if it has meaningful words
        meaningful_words = [
            "invoice",
            "receipt",
            "document",
            "scan",
            "contract",
            "report",
            "screenshot",
        ]
        if any(word in filename_lower for word in meaningful_words):
            return True
        return False

    return True


class AttachmentManager:
    """Manages downloading, saving, and parsing email attachments."""

    SUPPORTED_FORMATS = {
        "application/pdf": ".pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
        "application/msword": ".doc",
        "text/plain": ".txt",
        "text/csv": ".csv",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
        "application/vnd.ms-excel": ".xls",
        "text/html": ".html",
        "image/jpeg": ".jpg",
        "image/png": ".png",
    }

    def __init__(self, download_dir: str = "./attachments"):
        """Initialize attachment manager.

        Args:
            download_dir: Directory to save downloaded attachments
        """
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)

        if markitdown is None:
            print("⚠️  markitdown not installed. Install with: pip install markitdown")

    def download_attachment(
        self,
        gmail_service,
        message_id: str,
        attachment_id: str,
        filename: str,
        mime_type: str,
    ) -> Optional[Path]:
        """Download attachment from Gmail.

        Args:
            gmail_service: Gmail API service
            message_id: Gmail message ID
            attachment_id: Gmail attachment ID
            filename: Original filename
            mime_type: MIME type of attachment

        Returns:
            Path to downloaded file or None if failed
        """
        try:
            # Check if format is supported
            if mime_type not in self.SUPPORTED_FORMATS:
                return None

            # Get attachment data
            attachment_data = (
                gmail_service.users()
                .messages()
                .attachments()
                .get(userId="me", messageId=message_id, id=attachment_id)
                .execute()
            )

            file_data = base64.urlsafe_b64decode(attachment_data.get("data", ""))

            # Create safe filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_filename = f"{timestamp}_{filename}"
            file_path = self.download_dir / safe_filename

            # Save file
            with open(file_path, "wb") as f:
                f.write(file_data)

            return file_path

        except Exception as e:
            print(f"❌ Error downloading attachment {filename}: {e}")
            return None

    def parse_document(self, file_path: Path) -> Optional[Dict]:
        """Parse document using markitdown.

        Args:
            file_path: Path to document file

        Returns:
            Dictionary with parsed content and metadata
        """
        if markitdown is None:
            return None

        try:
            # Use markitdown to convert to markdown
            # The correct API is MarkitDown().convert() with a file path
            md = markitdown.MarkItDown()
            result = md.convert(str(file_path))
            content = result.text_content

            if not content:
                return None

            return {
                "filename": file_path.name,
                "file_path": str(file_path),
                "content": content,
                "content_length": len(content),
                "content_preview": content[:500],  # First 500 chars
                "mime_type": self._get_mime_type(file_path.suffix),
                "parsed_at": datetime.now().isoformat(),
            }

        except Exception as e:
            print(f"❌ Error parsing document {file_path.name}: {e}")
            return None

    def process_email_attachments(
        self,
        gmail_service,
        message_id: str,
        attachments_info: List[Dict],
    ) -> Dict:
        """Process all attachments for an email.

        Args:
            gmail_service: Gmail API service
            message_id: Gmail message ID
            attachments_info: List of attachment info from Gmail

        Returns:
            Dictionary with parsed attachments data
        """
        parsed_attachments = {
            "total": len(attachments_info),
            "downloaded": 0,
            "parsed": 0,
            "skipped": 0,
            "attachments": [],
            "content": [],  # All parsed content combined
            "errors": [],
        }

        for att in attachments_info:
            filename = att.get("filename", "unknown")
            mime_type = att.get("mimeType", "")
            attachment_id = att.get("attachmentId", "")

            # Skip irrelevant attachments (signatures, logos, inline images)
            if not is_relevant_attachment(filename, mime_type):
                parsed_attachments["skipped"] += 1
                continue

            # Download attachment
            file_path = self.download_attachment(
                gmail_service, message_id, attachment_id, filename, mime_type
            )

            if not file_path:
                parsed_attachments["errors"].append(
                    f"Could not download or unsupported format: {filename}"
                )
                continue

            parsed_attachments["downloaded"] += 1

            # Parse if text-based
            parsed_data = self.parse_document(file_path)

            if parsed_data:
                parsed_attachments["parsed"] += 1
                parsed_attachments["attachments"].append(parsed_data)
                parsed_attachments["content"].append(
                    f"### {parsed_data['filename']}\n\n{parsed_data['content']}"
                )
            else:
                # Still add non-parsed files to attachments list
                parsed_attachments["attachments"].append(
                    {
                        "filename": filename,
                        "file_path": str(file_path),
                        "content": None,
                        "mime_type": mime_type,
                        "parsed_at": datetime.now().isoformat(),
                    }
                )

        return parsed_attachments

    @staticmethod
    def _get_mime_type(suffix: str) -> str:
        """Get MIME type from file suffix."""
        mime_types = {
            ".pdf": "application/pdf",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".doc": "application/msword",
            ".txt": "text/plain",
            ".csv": "text/csv",
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ".xls": "application/vnd.ms-excel",
            ".html": "text/html",
            ".jpg": "image/jpeg",
            ".png": "image/png",
        }
        return mime_types.get(suffix.lower(), "application/octet-stream")

    def get_attachment_size_str(self, size_bytes: int) -> str:
        """Convert bytes to human-readable size."""
        for unit in ["B", "KB", "MB", "GB"]:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"

    def cleanup_old_attachments(self, days: int = 7):
        """Clean up attachments older than specified days.

        Args:
            days: Number of days to keep (default 7)
        """
        import time

        current_time = time.time()
        cutoff_time = current_time - (days * 24 * 60 * 60)

        cleaned = 0
        for file_path in self.download_dir.glob("*"):
            if file_path.stat().st_mtime < cutoff_time:
                file_path.unlink()
                cleaned += 1

        if cleaned > 0:
            print(f"🗑️  Cleaned up {cleaned} old attachments")

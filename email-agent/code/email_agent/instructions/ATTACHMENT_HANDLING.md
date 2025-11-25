# Attachment Handling Guide

Your email agent now has powerful attachment handling capabilities using **markitdown** to parse PDFs and documents.

## Features

### 1. **Automatic Attachment Download and Parsing**
- Attachments are automatically downloaded when emails are indexed
- Supported formats: PDF, DOCX, DOC, TXT, CSV, XLSX, XLS, HTML, JPG, PNG
- Text-based documents are parsed to markdown using `markitdown`
- Parsed content is stored in Elasticsearch for searching

### 2. **Search Attachments Tool**
The agent has a `search_attachments` tool that lets you search within attachment content:

```
User: "Find information about invoice totals in my attachments"
Agent: Uses search_attachments tool to search through all parsed PDFs
```

### 3. **How It Works**

**Email Fetching Process:**
1. Email is fetched from Gmail
2. Attachments are extracted from the email
3. Each attachment is downloaded to `./attachments/` directory
4. Text-based formats (PDF, DOCX, etc.) are parsed using `markitdown`
5. Parsed content is stored in Elasticsearch along with email metadata
6. Agent can now search and answer questions about attachment content

### 4. **Example Queries**

```
# Search in PDFs for specific text
"Find all mentions of 'budget' in my attachments"

# Search for specific document types
"What invoices do I have from Company X?"
"Find all contracts in my email attachments"

# Combined searches
"Show me emails from john@example.com with attachments about Q1 budget"
```

## Configuration

### Attachment Storage Directory
By default, attachments are saved to `./attachments/` in the project root.

To change this, modify in `main.py`:
```python
attachment_manager = AttachmentManager(download_dir="/custom/path")
```

### Supported MIME Types
The following formats are supported:
- `application/pdf` → PDF documents
- `application/vnd.openxmlformats-officedocument.wordprocessingml.document` → DOCX files
- `application/msword` → DOC files
- `text/plain` → TXT files
- `text/csv` → CSV files
- `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` → XLSX files
- `application/vnd.ms-excel` → XLS files
- `text/html` → HTML files
- `image/jpeg` → JPG images (OCR capable with markitdown)
- `image/png` → PNG images (OCR capable with markitdown)

## Data Model

### EmailAttachment Schema
Each attachment now includes:
```python
@dataclass
class EmailAttachment:
    filename: str                    # Original filename
    mime_type: str                   # MIME type
    attachment_id: str               # Gmail attachment ID
    size: int                        # File size in bytes
    content: Optional[bytes]         # Raw file content
    parsed_content: Optional[str]    # Markdown-parsed content
    file_path: Optional[str]         # Path to saved file
```

### Elasticsearch Storage
Attachment data in Elasticsearch includes:
```json
{
  "attachments": [
    {
      "filename": "invoice_2024.pdf",
      "mime_type": "application/pdf",
      "has_parsed_content": true,
      "parsed_content": "# Invoice 2024\n\nInvoice Number: INV-001...",
      "size": 45382
    }
  ]
}
```

## Advanced Usage

### Cleanup Old Attachments
The `AttachmentManager` can automatically clean up old downloaded files:

```python
from email_agent import AttachmentManager

manager = AttachmentManager()
manager.cleanup_old_attachments(days=7)  # Delete files older than 7 days
```

### Get Attachment Metadata
```python
from email_agent import AttachmentManager

manager = AttachmentManager()
size_str = manager.get_attachment_size_str(1048576)  # Returns "1.0 MB"
```

### Manual Parsing
You can also manually parse documents:

```python
from email_agent import AttachmentManager
from pathlib import Path

manager = AttachmentManager()
parsed = manager.parse_document(Path("document.pdf"))
print(parsed["content"])  # Markdown content
print(parsed["content_length"])  # Length of parsed content
```

## Markitdown Features

Markitdown is a powerful library that:
- ✅ Extracts text from PDFs
- ✅ Converts Office documents to markdown
- ✅ Extracts tables from documents
- ✅ Performs OCR on images
- ✅ Preserves document structure and formatting

For more info: https://github.com/microsoft/markitdown

## Installation

Ensure markitdown is installed:
```bash
cd /workspaces/ai-bootcamp/email-agent/code
uv pip install markitdown
```

Or it's included in `pyproject.toml` dependencies.

## Common Questions

### Q: Are attachments automatically parsed?
**A:** Yes! When emails are fetched and indexed, attachments are automatically downloaded and parsed.

### Q: What happens to original files?
**A:** Original files are saved in the `./attachments/` directory with timestamped names for easy tracking.

### Q: Can I search by attachment filename?
**A:** Yes! The agent can search for emails by attachment filename using `elasticsearch_search` tool.

### Q: How large can attachments be?
**A:** Gmail's limit is 25 MB per email. Markitdown can handle PDFs and documents of any reasonable size.

### Q: What if parsing fails for an attachment?
**A:** The attachment is still stored as a record, but the `parsed_content` field will be null. The agent will note that the attachment couldn't be parsed.

## Troubleshooting

### "markitdown not installed"
Install it with: `pip install markitdown`

### Attachment not searchable
1. Check that the attachment format is in SUPPORTED_FORMATS
2. Verify the email was re-indexed after adding the new tool
3. Check `processing_errors` in the email document for details

### PDF text extraction not working
- Verify the PDF is not image-only (markitdown can do OCR but may need additional setup)
- Check file permissions on the saved attachment file
- Review Elasticsearch logs for indexing errors

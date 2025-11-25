# Attachment Handling - Implementation Summary

## What Was Added

Your email agent now has complete attachment handling with document parsing using **markitdown**. Here's what was implemented:

## New Modules

### 1. `email_agent/attachments.py` (NEW)
**AttachmentManager class** - Handles all attachment operations:
- `download_attachment()` - Downloads attachments from Gmail
- `parse_document()` - Parses documents using markitdown (PDF, DOCX, TXT, etc.)
- `process_email_attachments()` - Processes all attachments for an email
- `cleanup_old_attachments()` - Removes old downloaded files

**Supported formats:**
- PDFs, Word documents (DOCX/DOC)
- Text files, CSV, Excel sheets (XLSX/XLS)
- HTML, Images (JPG, PNG)

## Modified Modules

### 2. `email_agent/schemas.py`
**Enhanced EmailAttachment:**
```python
@dataclass
class EmailAttachment:
    filename: str
    mime_type: str
    attachment_id: str
    size: int
    content: Optional[bytes]
    parsed_content: Optional[str]  # ← NEW: Markitdown-parsed content
    file_path: Optional[str]       # ← NEW: Path to saved file
```

**Updated EmailDocument:**
- `get_context_for_llm()` now includes parsed attachment content
- Attachments are included in LLM context for better answers

### 3. `email_agent/gmail_client.py`
**Updated EmailDocumentParser:**
- Now accepts `AttachmentManager` in constructor
- Extracts attachment info from emails
- Automatically downloads and parses attachments when emails are parsed
- `_extract_attachments_info()` - Helper to extract attachment metadata

**Process flow:**
```
Email fetched → Attachments extracted → Downloaded → Parsed → Stored in Elasticsearch
```

### 4. `email_agent/tools/__init__.py`
**NEW: SearchAttachmentsTool**
```python
class SearchAttachmentsTool:
    """Tool to search within parsed attachment content."""
    - name: "search_attachments"
    - Searches PDF, DOCX, and document content
    - Returns emails with matching attachments
```

### 5. `email_agent/agent.py`
**Updated EmailAgent:**
- Added `search_attachments` to system prompt
- Added function definition for `search_attachments` tool
- Agent can now decide when to search attachments vs. emails

### 6. `main.py`
**Updated initialization:**
```python
attachment_tool = SearchAttachmentsTool(es_store)
agent = EmailAgent(tools=[gmail_tool, search_tool, write_tool, 
                          conversation_tool, attachment_tool])
```

### 7. `pyproject.toml`
**Added dependency:**
```toml
dependencies = [
    ...,
    "markitdown",  # ← NEW
]
```

### 8. `email_agent/__init__.py`
**Exported new classes:**
- `AttachmentManager`
- `SearchAttachmentsTool`

## How It Works

### Attachment Processing Pipeline
1. **Email Indexing**: When emails are fetched, attachments are extracted
2. **Download**: Attachments downloaded to `./attachments/` directory
3. **Parse**: Text-based documents parsed to markdown using markitdown
4. **Store**: Parsed content stored in Elasticsearch
5. **Search**: Agent can search within attachments using new tool

### Agent Capabilities
The agent now understands queries like:

```
"Find information about invoices in my attachments"
"What does the Q1 budget PDF say?"
"Search my contracts for payment terms"
"Find all PDFs mentioning 'revenue'"
```

### Data Flow
```
Gmail Email with Attachment
    ↓
EmailDocumentParser (creates EmailDocument)
    ↓
AttachmentManager.process_email_attachments()
    ↓
- Downloads file to ./attachments/
- Parses with markitdown
- Extracts text content
    ↓
EmailAttachment with parsed_content filled
    ↓
Elasticsearch indexing
    ↓
SearchAttachmentsTool can search content
```

## Usage Examples

### Example 1: Simple Attachment Search
```
User: "Find my invoices"
Agent: Uses search_attachments tool to search for "invoice" in all attachments
Result: Returns emails with invoice PDFs, showing parsed content preview
```

### Example 2: Specific Content Search
```
User: "What's the total amount in my contracts?"
Agent: 
1. Uses search_attachments to find contracts
2. Parses the PDF content
3. Extracts the amount information
4. Returns answer with source
```

### Example 3: Combined Search
```
User: "Find all attachments from john@example.com about Q1"
Agent:
1. Uses conversation_history to get all emails from john@example.com
2. Uses search_attachments to filter for "Q1" mentions
3. Returns matched attachments with context
```

## File Structure
```
email-agent/code/
├── email_agent/
│   ├── __init__.py (updated)
│   ├── agent.py (updated)
│   ├── attachments.py (NEW)
│   ├── elasticsearch_store.py
│   ├── gmail_client.py (updated)
│   ├── schemas.py (updated)
│   └── tools/
│       └── __init__.py (updated - added SearchAttachmentsTool)
├── main.py (updated)
├── pyproject.toml (updated - added markitdown)
└── ATTACHMENT_HANDLING.md (NEW - detailed guide)
```

## Installation

Markitdown will be installed with:
```bash
cd /workspaces/ai-bootcamp/email-agent/code
pip install markitdown
# or
uv pip install markitdown
```

## Next Steps

1. **Install dependencies:**
   ```bash
   uv pip install -e .
   ```

2. **Run the agent:**
   ```bash
   make run
   ```

3. **Try attachment queries:**
   ```
   You: Find my PDF invoices
   You: What information is in the Q1 budget document?
   You: Search attachments for "total revenue"
   ```

## Technical Details

### Markitdown
- Microsoft's library for converting documents to markdown
- Supports: PDF, DOCX, PPTX, HTML, JSON, and images
- Can extract tables and preserve formatting
- Performs OCR on images

### Elasticsearch Integration
- Attachment content stored in nested fields
- Full-text search across all attachment content
- Metadata (filename, mime_type, size) indexed separately
- Searchable through the new `search_attachments` tool

### Performance
- Attachments downloaded on-demand (not pre-fetched)
- Parsing happens during indexing
- Parsed content cached in Elasticsearch
- Cleanup tool available to manage disk space

## Error Handling

If an attachment can't be parsed:
- Format may not be supported
- File may be corrupted
- Parsing may fail (note added to `processing_errors`)
- Attachment record still created, just without parsed content

The agent handles this gracefully and informs the user.

## Security Considerations

- Attachments saved to local disk with timestamps
- File paths stored in Elasticsearch metadata
- Access is file-system based (no built-in auth)
- Use `cleanup_old_attachments()` to manage disk space
- Sensitive attachments should be handled with care

---

**All ready!** Your email agent can now download, parse, and search through email attachments! 🎉

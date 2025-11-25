"""Main package initialization."""

from .agent import EmailAgent
from .gmail_client import (
    authenticate_gmail,
    EmailDocumentParser,
    fetch_and_index_all_emails,
)
from .elasticsearch_store import ElasticsearchEmailStore
from .schemas import EmailDocument, EmailAttachment, EmailThread
from .attachments import AttachmentManager
from .tools import (
    GmailFetchTool,
    ElasticsearchSearchTool,
    ElasticsearchWriteTool,
    ConversationHistoryTool,
    SearchAttachmentsTool,
)
from .evaluation_schemas import (
    CheckName,
    EvaluationCheck,
    EvaluationResult,
    TestQuestion,
    EvaluationDataset,
)
from .manual_evaluator import ManualEvaluator

__all__ = [
    "EmailAgent",
    "authenticate_gmail",
    "EmailDocumentParser",
    "fetch_and_index_all_emails",
    "ElasticsearchEmailStore",
    "EmailDocument",
    "EmailAttachment",
    "EmailThread",
    "AttachmentManager",
    "GmailFetchTool",
    "ElasticsearchSearchTool",
    "ElasticsearchWriteTool",
    "ConversationHistoryTool",
    "SearchAttachmentsTool",
    "CheckName",
    "EvaluationCheck",
    "EvaluationResult",
    "TestQuestion",
    "EvaluationDataset",
    "ManualEvaluator",
]

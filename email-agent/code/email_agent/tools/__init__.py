"""Email tools for the agent."""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
import re
import json
from openai import OpenAI

from ..elasticsearch_store import ElasticsearchEmailStore


# Initialize OpenAI client for NLU-based categorization
_openai_client = None


def get_openai_client():
    """Get or create OpenAI client."""
    global _openai_client
    if _openai_client is None:
        _openai_client = OpenAI()
    return _openai_client


def parse_relative_date(date_str: Optional[str]) -> Optional[str]:
    """Convert natural language date to YYYY-MM-DD format.

    Supports:
    - 'today', 'yesterday'
    - 'last week', 'past week', 'this week'
    - 'last month', 'past month', 'this month'
    - 'last X days', 'past X days'
    - 'X days ago'
    - Already formatted dates (YYYY-MM-DD)
    """
    if not date_str:
        return None

    date_str = date_str.lower().strip()
    today = datetime.now()

    # Already in correct format
    if re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
        return date_str

    # Simple keywords
    if date_str == "today":
        return today.strftime("%Y-%m-%d")
    elif date_str == "yesterday":
        return (today - timedelta(days=1)).strftime("%Y-%m-%d")

    # Week-based
    elif date_str in ("last week", "past week", "this week"):
        return (today - timedelta(days=7)).strftime("%Y-%m-%d")

    # Month-based
    elif date_str in ("last month", "past month", "this month"):
        return (today - timedelta(days=30)).strftime("%Y-%m-%d")

    # "last X days" or "past X days"
    match = re.match(r"(?:last|past)\s+(\d+)\s+days?", date_str)
    if match:
        days = int(match.group(1))
        return (today - timedelta(days=days)).strftime("%Y-%m-%d")

    # "X days ago"
    match = re.match(r"(\d+)\s+days?\s+ago", date_str)
    if match:
        days = int(match.group(1))
        return (today - timedelta(days=days)).strftime("%Y-%m-%d")

    # "last X weeks" or "past X weeks"
    match = re.match(r"(?:last|past)\s+(\d+)\s+weeks?", date_str)
    if match:
        weeks = int(match.group(1))
        return (today - timedelta(weeks=weeks)).strftime("%Y-%m-%d")

    # Return as-is if we can't parse (might be a date string)
    return date_str


# MIME types to skip (images used in signatures, inline graphics, etc.)
SKIP_ATTACHMENT_MIMES = {
    "image/gif",
    "image/x-icon",
    "image/bmp",
    # Note: image/jpeg and image/png can be relevant docs, but often are signatures
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

    # Skip images that are clearly inline (Content-ID often used)
    # But allow PDFs, docs, spreadsheets, etc.
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
    # Larger filenames (like "Invoice_2025.png") are more likely to be relevant
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
        ]
        if any(word in filename_lower for word in meaningful_words):
            return True
        return False

    return True


class GmailFetchTool:
    """Tool to fetch emails from Gmail API."""

    def __init__(self, gmail_service):
        self.service = gmail_service
        self.name = "gmail_fetch"
        self.description = (
            "Fetches emails from Gmail. Can fetch unread, read, or all emails."
        )

    def run(self, max_results: int = 10, query: str = "is:unread") -> List[Dict]:
        """Fetch emails from Gmail."""
        try:
            search_query = query if query else "in:inbox"

            results = (
                self.service.users()
                .messages()
                .list(userId="me", q=search_query, maxResults=max_results)
                .execute()
            )

            messages = results.get("messages", [])
            emails = []

            for msg in messages:
                email_data = (
                    self.service.users()
                    .messages()
                    .get(userId="me", id=msg["id"], format="full")
                    .execute()
                )

                parsed = self._parse_email(email_data)
                emails.append(parsed)

            return emails

        except Exception as e:
            return {"error": f"Failed to fetch emails: {str(e)}"}

    @staticmethod
    def _parse_email(email_data: Dict) -> Dict:
        """Parse Gmail API response into structured format."""
        headers = {
            h["name"].lower(): h["value"] for h in email_data["payload"]["headers"]
        }

        labels = email_data.get("labelIds", [])
        is_read = "UNREAD" not in labels

        return {
            "id": email_data["id"],
            "thread_id": email_data["threadId"],
            "sender": headers.get("from", ""),
            "subject": headers.get("subject", "(No Subject)"),
            "date": headers.get("date", ""),
            "snippet": email_data.get("snippet", ""),
            "labels": labels,
            "is_read": is_read,
        }


class ElasticsearchSearchTool:
    """Tool to search emails in Elasticsearch."""

    def __init__(self, es_store: ElasticsearchEmailStore):
        self.es_store = es_store
        self.name = "elasticsearch_search"
        self.description = """Search emails in Elasticsearch. Supports:
- search_text: keywords to search in subject/body
- sender: filter by sender email address
- recipient: filter by recipient email address
- category: filter by category
- date_from: start date (supports 'last week', 'past 7 days', 'yesterday', or 'YYYY-MM-DD')
- date_to: end date (supports same formats)
- has_attachments: true/false to filter by attachment presence
- labels: filter by Gmail labels (IMPORTANT, STARRED, etc.)
- is_read: true/false to filter read status"""

    def run(
        self,
        search_text: Optional[str] = None,
        sender: Optional[str] = None,
        recipient: Optional[str] = None,
        category: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        has_attachments: Optional[bool] = None,
        labels: Optional[List[str]] = None,
        is_read: Optional[bool] = None,
        max_results: int = 10,
    ) -> List[Dict]:
        """Search emails in Elasticsearch."""
        try:
            must_clauses = []
            filter_clauses = []

            if search_text:
                must_clauses.append(
                    {
                        "multi_match": {
                            "query": search_text,
                            "fields": ["subject^3", "body.plain^2", "snippet"],
                            "fuzziness": "AUTO",
                        }
                    }
                )

            if sender:
                # Search in sender email (partial match)
                must_clauses.append(
                    {
                        "bool": {
                            "should": [
                                {"wildcard": {"sender.email": f"*{sender.lower()}*"}},
                                {"match": {"sender.name": sender}},
                            ]
                        }
                    }
                )

            if recipient:
                # Search in recipients, cc, bcc
                must_clauses.append(
                    {
                        "bool": {
                            "should": [
                                {"wildcard": {"recipients": f"*{recipient.lower()}*"}},
                                {"wildcard": {"cc": f"*{recipient.lower()}*"}},
                                {"wildcard": {"bcc": f"*{recipient.lower()}*"}},
                            ]
                        }
                    }
                )

            if category:
                filter_clauses.append({"term": {"category": category}})

            # Parse relative dates
            parsed_date_from = parse_relative_date(date_from)
            parsed_date_to = parse_relative_date(date_to)

            if parsed_date_from or parsed_date_to:
                date_range = {}
                if parsed_date_from:
                    date_range["gte"] = parsed_date_from
                if parsed_date_to:
                    date_range["lte"] = parsed_date_to
                filter_clauses.append({"range": {"date": date_range}})

            # Filter by attachment presence
            if has_attachments is not None:
                filter_clauses.append({"term": {"has_attachments": has_attachments}})

            # Filter by labels (IMPORTANT, STARRED, etc.)
            if labels:
                for label in labels:
                    filter_clauses.append({"term": {"labels": label.upper()}})

            # Filter by read status
            if is_read is not None:
                filter_clauses.append({"term": {"is_read": is_read}})

            query = {
                "query": {
                    "bool": {
                        "must": must_clauses if must_clauses else [{"match_all": {}}],
                        "filter": filter_clauses if filter_clauses else [],
                    }
                },
                "size": max_results,
                "sort": [{"date": {"order": "desc"}}],
            }

            results = self.es_store.search(query)

            # Filter out irrelevant attachments from results
            for result in results:
                if result.get("attachments"):
                    result["attachments"] = [
                        att
                        for att in result["attachments"]
                        if is_relevant_attachment(
                            att.get("filename", ""), att.get("mime_type", "")
                        )
                    ]
                    result["attachment_count"] = len(result["attachments"])

            return results

        except Exception as e:
            return {"error": f"Search failed: {str(e)}"}


class ConversationHistoryTool:
    """Tool to fetch complete conversation history with a specific person/email."""

    def __init__(self, es_store: ElasticsearchEmailStore):
        self.es_store = es_store
        self.name = "conversation_history"
        self.description = """Fetch ALL emails in conversations with a specific person/company. 
Searches in sender, recipients, cc, and bcc fields to get the COMPLETE conversation thread.
Use this to understand full context with someone, like invoice history with a company.
Optionally filter by thread_id for a specific conversation."""

    def run(
        self,
        email_address: str,
        thread_id: Optional[str] = None,
        max_results: int = 100,
    ) -> Dict:
        """Get all emails involving a specific email address (as sender OR recipient)."""
        try:
            email_lower = email_address.lower()

            # Build query to search in sender, recipients, cc, bcc
            should_clauses = [
                {"wildcard": {"sender.email": f"*{email_lower}*"}},
                {"wildcard": {"recipients": f"*{email_lower}*"}},
                {"wildcard": {"cc": f"*{email_lower}*"}},
                {"wildcard": {"bcc": f"*{email_lower}*"}},
            ]

            must_clauses = [
                {"bool": {"should": should_clauses, "minimum_should_match": 1}}
            ]

            # Optionally filter by specific thread
            if thread_id:
                must_clauses.append({"term": {"thread_id": thread_id}})

            query = {
                "query": {"bool": {"must": must_clauses}},
                "size": max_results,
                "sort": [
                    {"date": {"order": "asc"}}
                ],  # Oldest first for conversation flow
            }

            results = self.es_store.search(query)

            # Group by thread_id to show full conversations
            threads = {}
            for email in results:
                tid = email.get("thread_id")
                if tid not in threads:
                    threads[tid] = []
                threads[tid].append(email)

            # Sort emails within each thread by date
            for tid in threads:
                threads[tid].sort(key=lambda x: x.get("date", ""))

            # Determine direction of each email (sent vs received)
            for email in results:
                sender = email.get("sender", {}).get("email", "").lower()
                if email_lower in sender:
                    email["direction"] = "from_contact"
                else:
                    email["direction"] = "to_contact"

            return {
                "contact": email_address,
                "total_emails": len(results),
                "thread_count": len(threads),
                "threads": threads,
                "emails": results,
            }

        except Exception as e:
            return {"error": f"Failed to get conversation history: {str(e)}"}


class ElasticsearchWriteTool:
    """Tool to write/update emails in Elasticsearch."""

    def __init__(self, es_store: ElasticsearchEmailStore):
        self.es_store = es_store
        self.name = "elasticsearch_write"
        self.description = "Writes or updates email documents in Elasticsearch."

    def run(self, email_id: str, updates: Dict) -> Dict:
        """Update an email document in Elasticsearch."""
        return self.es_store.update(email_id, updates)


class SearchAttachmentsTool:
    """Tool to search within parsed attachment content."""

    def __init__(self, es_store: ElasticsearchEmailStore):
        self.es_store = es_store
        self.name = "search_attachments"
        self.description = """Search for content within email attachments (PDFs, documents, spreadsheets, etc). 
Use this to find specific text/data in attached files.
Filters out irrelevant attachments like email signatures and logos.
Can also filter by file type (pdf, docx, xlsx, etc.) and sender."""

    def run(
        self,
        search_text: str,
        file_type: Optional[str] = None,
        sender: Optional[str] = None,
        date_from: Optional[str] = None,
        max_results: int = 10,
    ) -> List[Dict]:
        """Search within attachment content."""
        try:
            must_clauses = []
            filter_clauses = []

            # Must have attachments
            filter_clauses.append({"term": {"has_attachments": True}})

            # Try nested query for parsed content, but also search in regular fields
            # because ES mapping might not have nested properly indexed
            should_clauses = [
                # Search in email body/subject for attachment-related content
                {
                    "multi_match": {
                        "query": search_text,
                        "fields": ["subject^2", "body.plain", "snippet"],
                        "fuzziness": "AUTO",
                    }
                },
            ]

            # Try nested query if parsed content exists
            try:
                should_clauses.append(
                    {
                        "nested": {
                            "path": "attachments",
                            "query": {
                                "bool": {
                                    "should": [
                                        {
                                            "match": {
                                                "attachments.filename": search_text
                                            }
                                        },
                                        {
                                            "match": {
                                                "attachments.parsed_content": search_text
                                            }
                                        },
                                    ]
                                }
                            },
                        }
                    }
                )
            except Exception:
                pass  # Nested might not be configured

            must_clauses.append(
                {"bool": {"should": should_clauses, "minimum_should_match": 1}}
            )

            # Filter by file type
            if file_type:
                file_type_lower = file_type.lower().strip(".")
                mime_map = {
                    "pdf": "application/pdf",
                    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    "doc": "application/msword",
                    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    "xls": "application/vnd.ms-excel",
                    "csv": "text/csv",
                    "txt": "text/plain",
                }
                if file_type_lower in mime_map:
                    try:
                        filter_clauses.append(
                            {
                                "nested": {
                                    "path": "attachments",
                                    "query": {
                                        "term": {
                                            "attachments.mime_type": mime_map[
                                                file_type_lower
                                            ]
                                        }
                                    },
                                }
                            }
                        )
                    except Exception:
                        pass

            # Filter by sender
            if sender:
                must_clauses.append(
                    {
                        "bool": {
                            "should": [
                                {"wildcard": {"sender.email": f"*{sender.lower()}*"}},
                                {"match": {"sender.name": sender}},
                            ]
                        }
                    }
                )

            # Filter by date
            parsed_date_from = parse_relative_date(date_from)
            if parsed_date_from:
                filter_clauses.append({"range": {"date": {"gte": parsed_date_from}}})

            query = {
                "query": {"bool": {"must": must_clauses, "filter": filter_clauses}},
                "size": max_results * 2,  # Fetch extra to filter
                "sort": [{"date": {"order": "desc"}}],
            }

            results = self.es_store.search(query)

            # Filter and process results
            filtered_results = []
            for email in results:
                if email.get("attachments"):
                    # Filter out irrelevant attachments (signatures, logos, etc.)
                    relevant_attachments = [
                        att
                        for att in email.get("attachments", [])
                        if is_relevant_attachment(
                            att.get("filename", ""), att.get("mime_type", "")
                        )
                    ]

                    if not relevant_attachments:
                        continue

                    # Check if any attachment matches search text
                    matching_attachments = []
                    for att in relevant_attachments:
                        # Check filename
                        if search_text.lower() in att.get("filename", "").lower():
                            att["match_reason"] = "filename"
                            matching_attachments.append(att)
                        # Check parsed content
                        elif (
                            att.get("parsed_content")
                            and search_text.lower()
                            in att.get("parsed_content", "").lower()
                        ):
                            att["match_reason"] = "content"
                            # Add content preview
                            content = att.get("parsed_content", "")
                            idx = content.lower().find(search_text.lower())
                            if idx >= 0:
                                start = max(0, idx - 100)
                                end = min(len(content), idx + len(search_text) + 100)
                                att["content_preview"] = f"...{content[start:end]}..."
                            matching_attachments.append(att)

                    if matching_attachments:
                        email["matching_attachments"] = matching_attachments
                        email["attachments"] = relevant_attachments
                        filtered_results.append(email)
                    elif relevant_attachments:
                        # Include email if it has relevant attachments even without content match
                        # (content might not be indexed but search was in subject/body)
                        email["attachments"] = relevant_attachments
                        email["matching_attachments"] = []
                        filtered_results.append(email)

                if len(filtered_results) >= max_results:
                    break

            return filtered_results

        except Exception as e:
            return {"error": f"Attachment search failed: {str(e)}"}


# ============================================================================
# Email Categorization and Priority Tools
# ============================================================================

# Known spam/promotional sender patterns
SPAM_PROMOTIONAL_PATTERNS = [
    r"noreply@",
    r"no-reply@",
    r"newsletter@",
    r"marketing@",
    r"promo@",
    r"deals@",
    r"offers@",
    r"notifications@",
    r"updates@",
    r"news@",
    r"info@.*\.com$",  # Generic info@ addresses
    r"support@",  # Usually automated
    r"@mailchimp\.",
    r"@sendgrid\.",
    r"@constantcontact\.",
    r"@hubspot\.",
]

# Keywords indicating payment requests
PAYMENT_KEYWORDS = [
    "invoice",
    "payment",
    "pay",
    "amount due",
    "remittance",
    "wire transfer",
    "bank transfer",
    "ach",
    "billing",
    "statement",
    "outstanding balance",
    "past due",
    "overdue",
    "receipt",
    "purchase order",
    "po#",
    "p.o.",
]

# Keywords indicating urgent/action-required emails
URGENT_KEYWORDS = [
    "urgent",
    "asap",
    "immediately",
    "action required",
    "response needed",
    "please respond",
    "time sensitive",
    "deadline",
    "due date",
    "expiring",
    "expires",
    "final notice",
    "last chance",
    "reminder",
    "follow up",
    "following up",
    "awaiting",
    "waiting for",
    "pending",
    "approval needed",
    "please confirm",
    "confirmation needed",
    "request",
    "requesting",
    "need your",
    "require",
    "required",
]

# Service request keywords (highest priority)
SERVICE_REQUEST_KEYWORDS = [
    "quote",
    "quotation",
    "proposal",
    "estimate",
    "pricing",
    "service request",
    "new order",
    "place order",
    "order request",
    "booking",
    "schedule",
    "appointment",
    "consultation",
    "inquiry",
    "interested in",
    "would like to",
    "looking for",
    "need help",
    "assistance",
    "support request",
]


def is_spam_or_promotional(sender_email: str, subject: str, labels: List[str]) -> bool:
    """Check if email is spam or promotional."""
    sender_lower = sender_email.lower()
    subject_lower = subject.lower()

    # Check Gmail labels
    promo_labels = {
        "CATEGORY_PROMOTIONS",
        "CATEGORY_SOCIAL",
        "SPAM",
    }
    if any(label in promo_labels for label in labels):
        return True

    # Check sender patterns
    for pattern in SPAM_PROMOTIONAL_PATTERNS:
        if re.search(pattern, sender_lower):
            return True

    # Check subject for promotional keywords
    promo_subject_words = [
        "unsubscribe",
        "newsletter",
        "weekly digest",
        "sale",
        "% off",
        "discount",
        "deal",
    ]
    if any(word in subject_lower for word in promo_subject_words):
        return True

    return False


def categorize_email_with_llm(email: Dict) -> Dict:
    """Use LLM to categorize an email with natural language understanding.

    Returns dict with:
    - category: payment_request, service_request, client_communication, internal, promotional, spam
    - is_payment_request: bool
    - is_from_mys: bool (if sender is MYS USA / mysusainc.com)
    - urgency: high, medium, low
    - needs_response: bool
    - summary: brief description
    """
    client = get_openai_client()

    # Extract email content
    sender = email.get("sender", {})
    sender_email = sender.get("email", "") if isinstance(sender, dict) else str(sender)
    sender_name = sender.get("name", "") if isinstance(sender, dict) else ""
    subject = email.get("subject", "")
    body = email.get("body", {})
    body_text = (
        body.get("plain", "")[:1500] if isinstance(body, dict) else str(body)[:1500]
    )
    snippet = email.get("snippet", "")

    prompt = f"""Analyze this email and categorize it. Respond in JSON format only.

EMAIL:
From: {sender_name} <{sender_email}>
Subject: {subject}
Preview: {snippet}
Body: {body_text}

Determine:
1. category: One of: "payment_request", "service_request", "client_communication", "internal", "promotional", "automated_notification", "spam"
2. is_payment_request: Is this asking for money/payment to be made? (invoice, bill, request for funds, etc.) - true/false
3. is_from_mys: Is the sender from MYS USA, MYS Inc, mysusainc.com, or similar? - true/false  
4. urgency: "high", "medium", or "low"
5. needs_response: Does this email require a reply? - true/false
6. summary: One sentence description

IMPORTANT: 
- "payment_request" means someone is asking YOU to pay THEM (they sent an invoice, bill, payment request)
- If from MYS USA (mysusainc.com, quickbooks with "MYS" in subject), set is_from_mys=true
- Automated notifications from services (QuickBooks, banks, etc) should still be categorized by their content

Respond ONLY with valid JSON, no other text:"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=300,
        )

        result_text = response.choices[0].message.content.strip()
        # Clean up potential markdown code blocks
        if result_text.startswith("```"):
            result_text = result_text.split("```")[1]
            if result_text.startswith("json"):
                result_text = result_text[4:]
        result_text = result_text.strip()

        return json.loads(result_text)
    except Exception as e:
        # Fallback to basic categorization on error
        return {
            "category": "client_communication",
            "is_payment_request": False,
            "is_from_mys": "mys" in sender_email.lower(),
            "urgency": "medium",
            "needs_response": False,
            "summary": subject,
            "error": str(e),
        }


def calculate_priority_with_llm(
    email: Dict, category_info: Optional[Dict] = None
) -> Dict:
    """Calculate priority score using LLM understanding.

    Returns dict with:
    - score: 0-100
    - priority_level: critical, high, medium, low
    - reasons: list of reasons
    """
    # Use provided category info or get it
    if category_info is None:
        category_info = categorize_email_with_llm(email)

    score = 50  # Base score
    reasons = []

    # Service requests are highest priority
    if category_info.get("category") == "service_request":
        score += 30
        reasons.append("Service/quote request")

    # Payment requests (excluding your own company's invoices)
    if category_info.get("is_payment_request") and not category_info.get("is_from_mys"):
        score += 20
        reasons.append("External payment request")

    # Urgency from LLM
    urgency = category_info.get("urgency", "medium")
    if urgency == "high":
        score += 25
        reasons.append("High urgency")
    elif urgency == "low":
        score -= 10

    # Needs response
    if category_info.get("needs_response"):
        score += 15
        reasons.append("Needs response")

    # Gmail labels
    labels = email.get("labels", [])
    if "IMPORTANT" in labels:
        score += 10
        reasons.append("Marked important")
    if "STARRED" in labels:
        score += 10
        reasons.append("Starred")
    if "UNREAD" in labels:
        score += 5
        reasons.append("Unread")

    # Penalize promotional/spam
    if category_info.get("category") in (
        "promotional",
        "spam",
        "automated_notification",
    ):
        score -= 40
        reasons.append("Promotional/automated")

    # Determine priority level
    if score >= 80:
        priority_level = "critical"
    elif score >= 65:
        priority_level = "high"
    elif score >= 40:
        priority_level = "medium"
    else:
        priority_level = "low"

    return {
        "score": min(max(score, 0), 100),
        "priority_level": priority_level,
        "reasons": reasons,
        "category_info": category_info,
    }


# Keep legacy function for backward compatibility
def is_payment_request(subject: str, body: str) -> bool:
    """Check if email is a payment request (legacy keyword-based, use categorize_email_with_llm for better results)."""
    text = f"{subject} {body}".lower()
    return any(keyword in text for keyword in PAYMENT_KEYWORDS)


def calculate_priority_score(email: Dict) -> Dict:
    """Calculate priority score for an email (0-100)."""
    score = 50  # Base score
    reasons = []

    subject = email.get("subject", "").lower()
    body = email.get("body", {})
    body_text = body.get("plain", "") if isinstance(body, dict) else str(body)
    body_lower = body_text.lower()
    snippet = email.get("snippet", "").lower()
    text = f"{subject} {body_lower} {snippet}"
    labels = email.get("labels", [])

    # Check for service requests (highest priority boost)
    service_matches = [kw for kw in SERVICE_REQUEST_KEYWORDS if kw in text]
    if service_matches:
        score += 30
        reasons.append(f"Service request: {', '.join(service_matches[:3])}")

    # Check for urgent keywords
    urgent_matches = [kw for kw in URGENT_KEYWORDS if kw in text]
    if urgent_matches:
        score += 20
        reasons.append(f"Urgent: {', '.join(urgent_matches[:3])}")

    # Check for payment-related
    if is_payment_request(subject, body_lower):
        score += 15
        reasons.append("Payment related")

    # Gmail important label
    if "IMPORTANT" in labels:
        score += 10
        reasons.append("Marked important")

    # Starred
    if "STARRED" in labels:
        score += 10
        reasons.append("Starred")

    # Unread emails get slight boost
    if "UNREAD" in labels or not email.get("is_read", True):
        score += 5
        reasons.append("Unread")

    # Has attachments (might need review)
    if email.get("has_attachments") or email.get("attachment_count", 0) > 0:
        score += 5
        reasons.append("Has attachments")

    # Question marks in subject (likely needs response)
    if "?" in subject:
        score += 10
        reasons.append("Contains question")

    # Penalize promotional/spam
    sender = email.get("sender", {})
    sender_email = sender.get("email", "") if isinstance(sender, dict) else str(sender)
    if is_spam_or_promotional(sender_email, subject, labels):
        score -= 50
        reasons.append("Promotional/spam")

    return {
        "score": min(max(score, 0), 100),  # Clamp 0-100
        "reasons": reasons,
        "priority_level": "high" if score >= 70 else "medium" if score >= 40 else "low",
    }


class CategorizeEmailsTool:
    """Tool to categorize emails by type using LLM understanding (payment requests, MYS vs non-MYS, etc.)."""

    def __init__(self, es_store: ElasticsearchEmailStore):
        self.es_store = es_store
        self.name = "categorize_emails"
        self.description = """Categorize emails using AI to understand intent. Categories include:
- payment_request_non_mys: Payment requests NOT from MYS USA (external invoices/bills to pay)
- payment_request_mys: Payment requests FROM MYS USA (your company's invoices - usually ignore)
- service_request: Quote requests, orders, inquiries from clients
- client_email: General client communication
- promotional: Marketing/newsletters
- automated: System notifications

Uses natural language understanding - not just keywords."""

    def run(
        self,
        category_filter: Optional[str] = None,
        date_from: Optional[str] = None,
        max_results: int = 20,
    ) -> Dict:
        """Categorize emails using LLM understanding."""
        try:
            # Build query
            must_clauses = []

            # Parse date filter
            parsed_date_from = parse_relative_date(date_from)
            if parsed_date_from:
                must_clauses.append({"range": {"date": {"gte": parsed_date_from}}})

            query = {
                "query": {
                    "bool": {
                        "must": must_clauses if must_clauses else [{"match_all": {}}],
                    }
                },
                "size": max_results * 2,  # Fetch extra for categorization
                "sort": [{"date": {"order": "desc"}}],
            }

            results = self.es_store.search(query)

            # Categorize each email using LLM
            categorized = {
                "payment_request_non_mys": [],
                "payment_request_mys": [],
                "service_request": [],
                "client_email": [],
                "promotional": [],
                "automated": [],
                "other": [],
            }

            for email in results:
                # Use LLM to understand the email
                category_info = categorize_email_with_llm(email)
                email["_category_info"] = category_info

                is_payment = category_info.get("is_payment_request", False)
                is_mys = category_info.get("is_from_mys", False)
                category = category_info.get("category", "other")

                # Categorize based on LLM understanding
                if is_payment:
                    if is_mys:
                        categorized["payment_request_mys"].append(email)
                    else:
                        categorized["payment_request_non_mys"].append(email)
                elif category == "service_request":
                    categorized["service_request"].append(email)
                elif category in ("promotional", "spam"):
                    categorized["promotional"].append(email)
                elif category == "automated_notification":
                    categorized["automated"].append(email)
                elif category in ("client_communication", "internal"):
                    categorized["client_email"].append(email)
                else:
                    categorized["other"].append(email)

            # Apply category filter if specified
            if category_filter and category_filter in categorized:
                filtered = categorized[category_filter][:max_results]
                return {
                    "category": category_filter,
                    "count": len(filtered),
                    "emails": [
                        {
                            "subject": e.get("subject"),
                            "sender": e.get("sender"),
                            "date": e.get("date"),
                            "snippet": e.get("snippet"),
                            "analysis": e.get("_category_info", {}),
                        }
                        for e in filtered
                    ],
                }

            # Return summary with counts and samples
            summary = {k: len(v) for k, v in categorized.items()}

            # Format sample emails for each category
            samples = {}
            for cat, emails in categorized.items():
                samples[cat] = [
                    {
                        "subject": e.get("subject"),
                        "sender": e.get("sender"),
                        "date": e.get("date"),
                        "analysis": e.get("_category_info", {}).get("summary", ""),
                    }
                    for e in emails[:3]  # Top 3 from each
                ]

            return {
                "summary": summary,
                "non_mys_payment_requests": len(categorized["payment_request_non_mys"]),
                "samples": samples,
            }

        except Exception as e:
            return {"error": f"Categorization failed: {str(e)}"}


class PriorityInboxTool:
    """Tool to get priority-ranked emails that need attention/response using LLM understanding."""

    def __init__(self, es_store: ElasticsearchEmailStore):
        self.es_store = es_store
        self.name = "priority_inbox"
        self.description = """Get emails ranked by priority using AI understanding. Filters out spam and promotional.
Prioritizes based on:
- Service requests (quotes, orders, inquiries) - HIGHEST
- External payment requests (not from MYS)
- Urgent/time-sensitive emails
- Emails that need a response
- Emails marked important/starred

Uses natural language understanding to determine true urgency."""

    def run(
        self,
        date_from: Optional[str] = None,
        unread_only: bool = False,
        min_priority: str = "medium",  # low, medium, high, critical
        max_results: int = 15,
    ) -> Dict:
        """Get priority-ranked emails using LLM understanding."""
        try:
            must_clauses = []

            # Date filter
            parsed_date_from = parse_relative_date(date_from) or parse_relative_date(
                "last week"
            )
            must_clauses.append({"range": {"date": {"gte": parsed_date_from}}})

            # Optionally filter to unread only
            if unread_only:
                must_clauses.append({"term": {"is_read": False}})

            query = {
                "query": {
                    "bool": {
                        "must": must_clauses,
                    }
                },
                "size": max_results * 2,  # Fetch extra for scoring/filtering
                "sort": [{"date": {"order": "desc"}}],
            }

            results = self.es_store.search(query)

            # Score emails using LLM
            scored_emails = []
            priority_threshold = {"critical": 80, "high": 65, "medium": 40, "low": 0}
            min_score = priority_threshold.get(min_priority, 40)

            for email in results:
                # Get LLM-based category and priority
                category_info = categorize_email_with_llm(email)
                priority_info = calculate_priority_with_llm(email, category_info)

                # Skip if below threshold
                if priority_info["score"] < min_score:
                    continue

                # Skip promotional/spam
                if category_info.get("category") in ("promotional", "spam"):
                    continue

                email["_priority"] = priority_info
                email["_analysis"] = category_info
                scored_emails.append(email)

            # Sort by priority score (highest first)
            scored_emails.sort(key=lambda x: x["_priority"]["score"], reverse=True)

            # Take top results
            top_emails = scored_emails[:max_results]

            # Group by priority level
            by_priority = {
                "critical": [],
                "high": [],
                "medium": [],
                "low": [],
            }
            for e in top_emails:
                level = e["_priority"]["priority_level"]
                by_priority[level].append(
                    {
                        "subject": e.get("subject"),
                        "sender": e.get("sender"),
                        "date": e.get("date"),
                        "snippet": e.get("snippet", "")[:100],
                        "priority_score": e["_priority"]["score"],
                        "reasons": e["_priority"]["reasons"],
                        "needs_response": e.get("_analysis", {}).get(
                            "needs_response", False
                        ),
                        "summary": e.get("_analysis", {}).get("summary", ""),
                    }
                )

            return {
                "total_found": len(scored_emails),
                "returned": len(top_emails),
                "counts": {
                    "critical": len(by_priority["critical"]),
                    "high": len(by_priority["high"]),
                    "medium": len(by_priority["medium"]),
                    "low": len(by_priority["low"]),
                },
                "by_priority": by_priority,
            }

        except Exception as e:
            return {"error": f"Priority inbox failed: {str(e)}"}

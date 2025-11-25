"""Email tools for the agent."""

from typing import Dict, List, Optional

from ..elasticsearch_store import ElasticsearchEmailStore


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
        self.description = "Searches emails in Elasticsearch by sender, subject, date, category, or keywords."

    def run(
        self,
        search_text: Optional[str] = None,
        sender: Optional[str] = None,
        category: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        max_results: int = 10,
    ) -> List[Dict]:
        """Search emails in Elasticsearch."""
        try:
            must_clauses = []

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
                must_clauses.append({"match": {"sender.email": sender}})

            if category:
                must_clauses.append({"term": {"category": category}})

            if date_from or date_to:
                date_range = {}
                if date_from:
                    date_range["gte"] = date_from
                if date_to:
                    date_range["lte"] = date_to
                must_clauses.append({"range": {"date": date_range}})

            query = {
                "query": {
                    "bool": {
                        "must": must_clauses if must_clauses else [{"match_all": {}}]
                    }
                },
                "size": max_results,
                "sort": [{"date": {"order": "desc"}}],
            }

            results = self.es_store.search(query)
            return results

        except Exception as e:
            return {"error": f"Search failed: {str(e)}"}


class ConversationHistoryTool:
    """Tool to fetch complete conversation history with a specific person/email."""

    def __init__(self, es_store: ElasticsearchEmailStore):
        self.es_store = es_store
        self.name = "conversation_history"
        self.description = "Fetches ALL emails from a specific sender to see complete conversation history. Use this to understand full context with someone, like invoice history with a company."

    def run(self, sender_email: str, max_results: int = 100) -> Dict:
        """Get all emails from a specific sender."""
        try:
            query = {
                "query": {
                    "bool": {"must": [{"match": {"sender.email": sender_email}}]}
                },
                "size": max_results,
                "sort": [
                    {"date": {"order": "asc"}}
                ],  # Oldest first for conversation flow
            }

            results = self.es_store.search(query)

            # Group by thread_id to show full conversations
            threads = {}
            for email in results:
                thread_id = email.get("thread_id")
                if thread_id not in threads:
                    threads[thread_id] = []
                threads[thread_id].append(email)

            return {
                "sender": sender_email,
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
        self.description = "Search for content within email attachments (PDFs, documents, etc). Use this to find information in attached files."

    def run(self, search_text: str, max_results: int = 10) -> List[Dict]:
        """Search within attachment content."""
        try:
            query = {
                "query": {
                    "bool": {
                        "must": [
                            {
                                "nested": {
                                    "path": "attachments",
                                    "query": {
                                        "multi_match": {
                                            "query": search_text,
                                            "fields": [
                                                "attachments.filename",
                                                "attachments.parsed_content",
                                            ],
                                            "fuzziness": "AUTO",
                                        }
                                    },
                                }
                            }
                        ]
                    }
                },
                "size": max_results,
                "sort": [{"date": {"order": "desc"}}],
            }

            results = self.es_store.search(query)

            # Filter results to only return emails with matching attachments
            filtered_results = []
            for email in results:
                if email.get("attachments"):
                    # Only include attachments that have parsed content
                    matching_attachments = [
                        att
                        for att in email.get("attachments", [])
                        if att.get("parsed_content")
                        and search_text.lower() in att.get("parsed_content", "").lower()
                    ]
                    if matching_attachments:
                        email["matching_attachments"] = matching_attachments
                        filtered_results.append(email)

            return filtered_results

        except Exception as e:
            return {"error": f"Attachment search failed: {str(e)}"}

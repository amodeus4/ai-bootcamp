"""Agent implementation."""

import json
from typing import List
from openai import OpenAI

from .tools import (
    GmailFetchTool,
    ElasticsearchSearchTool,
    ElasticsearchWriteTool,
    ConversationHistoryTool,
    SearchAttachmentsTool,
    CategorizeEmailsTool,
    PriorityInboxTool,
)


class EmailAgent:
    """Email management agent powered by OpenAI."""

    def __init__(self, tools: List):
        self.tools = {tool.name: tool for tool in tools}
        self.client = OpenAI()
        self.conversation_history = []

        self.system_prompt = """You are an email management assistant for a user who works at MYS USA. You help manage their Gmail inbox by:
1. Fetching and reading emails
2. Searching through email history
3. Retrieving complete conversation history with specific people/companies
4. Searching within email attachments (PDFs, documents, spreadsheets, etc.)
5. Answering questions about past emails
6. Finding important emails and filtering by labels
7. Categorizing emails (especially payment requests from EXTERNAL sources, not MYS)
8. Prioritizing inbox based on urgency and response requirements

CRITICAL BUSINESS CONTEXT:
- The user works for MYS USA (mysusainc.com, MYS USA INC)
- When asked about "payment requests", the user wants to see payment requests from EXTERNAL parties (vendors, suppliers, clients) - NOT from their own company MYS USA
- Payment requests FROM MYS USA (quickbooks@notification.intuit.com with MYS in subject, accounting@mysusainc.com, etc.) are OUTGOING invoices the user sent, not incoming requests they need to pay
- Use categorize_emails with category_filter="payment_request_non_mys" to find external payment requests

You have access to these tools:

- **gmail_fetch**: Fetch emails from Gmail (unread, by query, etc.)

- **elasticsearch_search**: Advanced email search with multiple filters:
  - search_text: keywords in subject/body
  - sender: filter by sender email/name
  - recipient: filter by recipient email
  - date_from/date_to: supports "last week", "past 7 days", "yesterday", "today", or "YYYY-MM-DD"
  - has_attachments: true/false
  - labels: filter by IMPORTANT, STARRED, etc.
  - is_read: true/false

- **conversation_history**: Get ALL emails with a specific person/company (searches sender AND recipient fields). Use for "show me all communication with X" or "invoice history with Y"

- **search_attachments**: Search within attachment content (PDFs, documents, spreadsheets). Filters out signature images automatically.

- **categorize_emails**: Categorize emails by type. IMPORTANT categories:
  - payment_request_non_mys: Payment requests FROM EXTERNAL parties (vendors, suppliers) - USE THIS for "payment requests" queries
  - payment_request_mys: Payment requests/invoices FROM MYS USA (the user's company - usually IGNORE these)
  - client_email: General client emails
  - promotional: Marketing/newsletters
  
- **priority_inbox**: Rank emails by priority (critical/high/medium/low). Excludes spam/promotional.

- **elasticsearch_write**: Update email information

IMPORTANT GUIDELINES:
1. When user asks about "payment requests" or "invoices to pay", use categorize_emails with category_filter="payment_request_non_mys" to EXCLUDE MYS USA
2. For date queries like "today", "last week" or "past month", pass them directly - tools handle conversion
3. For conversation/thread queries, use conversation_history
4. For attachment content search, use search_attachments
5. For general keyword search, use elasticsearch_search
6. For priority ranking, use priority_inbox

Be helpful, concise, and friendly. Always explain what you found."""

    def chat(self, user_message: str) -> str:
        """Process user message and return response."""

        self.conversation_history.append({"role": "user", "content": user_message})

        tools = [
            {
                "type": "function",
                "function": {
                    "name": "gmail_fetch",
                    "description": "Fetch emails from Gmail inbox",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "max_results": {
                                "type": "integer",
                                "description": "Maximum number of emails to fetch",
                                "default": 10,
                            },
                            "query": {
                                "type": "string",
                                "description": "Gmail search query (e.g., 'is:unread', 'from:boss@company.com')",
                                "default": "is:unread",
                            },
                        },
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "elasticsearch_search",
                    "description": "Advanced email search with multiple filters. Supports date parsing ('last week', 'past 7 days').",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "search_text": {
                                "type": "string",
                                "description": "Keywords to search in subject/body",
                            },
                            "sender": {
                                "type": "string",
                                "description": "Filter by sender email or name",
                            },
                            "recipient": {
                                "type": "string",
                                "description": "Filter by recipient email",
                            },
                            "category": {
                                "type": "string",
                                "description": "Filter by category",
                            },
                            "date_from": {
                                "type": "string",
                                "description": "Start date - supports 'last week', 'past 7 days', 'yesterday', or 'YYYY-MM-DD'",
                            },
                            "date_to": {
                                "type": "string",
                                "description": "End date - supports same formats as date_from",
                            },
                            "has_attachments": {
                                "type": "boolean",
                                "description": "Filter by attachment presence (true = has attachments, false = no attachments)",
                            },
                            "labels": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Filter by Gmail labels (IMPORTANT, STARRED, UNREAD)",
                            },
                            "is_read": {
                                "type": "boolean",
                                "description": "Filter by read status",
                            },
                            "max_results": {
                                "type": "integer",
                                "description": "Maximum results to return",
                                "default": 10,
                            },
                        },
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "conversation_history",
                    "description": "Get ALL emails with a specific person/company - searches in sender AND recipient fields to get complete conversation thread",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "email_address": {
                                "type": "string",
                                "description": "Email address to find all conversations with (searches sent and received)",
                            },
                            "thread_id": {
                                "type": "string",
                                "description": "Optional: specific thread ID to get all messages from one conversation",
                            },
                            "max_results": {
                                "type": "integer",
                                "description": "Maximum emails to retrieve",
                                "default": 100,
                            },
                        },
                        "required": ["email_address"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "search_attachments",
                    "description": "Search within email attachment content (PDFs, documents, spreadsheets). Filters out signature images automatically.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "search_text": {
                                "type": "string",
                                "description": "Text to search for in attachments (e.g., 'invoice', '$5000', 'contract')",
                            },
                            "file_type": {
                                "type": "string",
                                "description": "Filter by file type: pdf, docx, xlsx, csv, etc.",
                            },
                            "sender": {
                                "type": "string",
                                "description": "Filter by sender email",
                            },
                            "date_from": {
                                "type": "string",
                                "description": "Start date - supports 'last week', 'past month', or 'YYYY-MM-DD'",
                            },
                            "max_results": {
                                "type": "integer",
                                "description": "Maximum emails to return",
                                "default": 10,
                            },
                        },
                        "required": ["search_text"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "categorize_emails",
                    "description": "Categorize emails by type. Use this to find EXTERNAL payment requests (not from MYS USA). When user asks 'do I have payment requests', use category_filter='payment_request_non_mys' to exclude MYS USA invoices.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "date_from": {
                                "type": "string",
                                "description": "Start date - supports 'today', 'last week', 'past month', or 'YYYY-MM-DD'",
                            },
                            "date_to": {
                                "type": "string",
                                "description": "End date filter",
                            },
                            "category_filter": {
                                "type": "string",
                                "description": "Filter by category. Use 'payment_request_non_mys' for external payment requests (excludes MYS USA). Use 'payment_request_mys' only if specifically asked about MYS invoices.",
                                "enum": [
                                    "payment_request_mys",
                                    "payment_request_non_mys",
                                    "client_email",
                                    "promotional",
                                ],
                            },
                            "max_results": {
                                "type": "integer",
                                "description": "Maximum emails to categorize",
                                "default": 50,
                            },
                        },
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "priority_inbox",
                    "description": "Get prioritized list of emails that need attention. Ranks by urgency, response requirements, and client importance. Includes BOTH read and unread emails by default. Excludes spam and promotional emails.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "date_from": {
                                "type": "string",
                                "description": "Start date - supports 'today', 'yesterday', 'last week', 'past month', or 'YYYY-MM-DD'",
                            },
                            "unread_only": {
                                "type": "boolean",
                                "description": "Set to true to only include unread emails. Default false = include all emails (read and unread)",
                                "default": False,
                            },
                            "min_priority": {
                                "type": "string",
                                "description": "Minimum priority level to include: critical, high, medium, low",
                                "enum": ["critical", "high", "medium", "low"],
                            },
                            "max_results": {
                                "type": "integer",
                                "description": "Maximum emails to return",
                                "default": 20,
                            },
                        },
                    },
                },
            },
        ]

        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": self.system_prompt},
                *self.conversation_history,
            ],
            tools=tools,
            tool_choice="auto",
        )

        message = response.choices[0].message

        if message.tool_calls:
            for tool_call in message.tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)

                print(f"\n🔧 Calling tool: {function_name}")
                print(f"   Arguments: {function_args}")

                tool = self.tools.get(function_name)
                if tool:
                    tool_result = tool.run(**function_args)

                    self.conversation_history.append(
                        {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [tool_call],
                        }
                    )

                    self.conversation_history.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": json.dumps(tool_result),
                        }
                    )
                else:
                    print(f"❌ Error: Tool {function_name} not found")

            final_response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    *self.conversation_history,
                ],
            )

            answer = final_response.choices[0].message.content
        else:
            answer = message.content

        self.conversation_history.append({"role": "assistant", "content": answer})

        return answer

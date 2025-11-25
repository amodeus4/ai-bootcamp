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
)


class EmailAgent:
    """Email management agent powered by OpenAI."""

    def __init__(self, tools: List):
        self.tools = {tool.name: tool for tool in tools}
        self.client = OpenAI()
        self.conversation_history = []

        self.system_prompt = """You are an email management assistant. You help users manage their Gmail inbox by:
1. Fetching and reading emails
2. Searching through email history
3. Retrieving complete conversation history with specific people/companies
4. Searching within email attachments (PDFs, documents, etc.)
5. Answering questions about past emails
6. Classifying emails into categories

You have access to these tools:
- gmail_fetch: Fetch unread emails from Gmail
- elasticsearch_search: Search through email history by sender, subject, keywords, category, or date
- conversation_history: Fetch ALL emails from a specific sender to see the complete discussion history (use this for questions like "what invoices from Company X" or "all communication with person Y")
- search_attachments: Search for content within email attachments (PDFs, documents, etc.) - use this when users ask about information in attached files
- elasticsearch_write: Update email information in the database

When a user asks a question:
1. Determine which tool(s) you need to use
2. If they ask about history with a specific person/company, use conversation_history
3. If they ask about content in attachments or PDFs, use search_attachments
4. For general searches in email body/subject, use elasticsearch_search
5. Call the appropriate tool with the right parameters
6. Provide a clear, conversational answer based on the results

Be helpful, concise, and friendly."""

    def chat(self, user_message: str) -> str:
        """Process user message and return response."""

        self.conversation_history.append({"role": "user", "content": user_message})

        tools = [
            {
                "type": "function",
                "function": {
                    "name": "gmail_fetch",
                    "description": "Fetch unread emails from Gmail",
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
                                "description": "Gmail search query",
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
                    "description": "Search emails by sender, keywords, category, or date",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "search_text": {
                                "type": "string",
                                "description": "Text to search in subject/body",
                            },
                            "sender": {
                                "type": "string",
                                "description": "Filter by sender email",
                            },
                            "category": {
                                "type": "string",
                                "description": "Filter by category",
                            },
                            "date_from": {
                                "type": "string",
                                "description": "Start date YYYY-MM-DD",
                            },
                            "date_to": {
                                "type": "string",
                                "description": "End date YYYY-MM-DD",
                            },
                            "max_results": {
                                "type": "integer",
                                "description": "Maximum results",
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
                    "description": "Fetch ALL emails from a specific sender to see complete conversation history",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "sender_email": {
                                "type": "string",
                                "description": "Email address to fetch all conversations with",
                            },
                            "max_results": {
                                "type": "integer",
                                "description": "Maximum emails to retrieve",
                                "default": 100,
                            },
                        },
                        "required": ["sender_email"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "search_attachments",
                    "description": "Search for content within email attachments (PDFs, documents, etc.)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "search_text": {
                                "type": "string",
                                "description": "Text to search for in attachments",
                            },
                            "max_results": {
                                "type": "integer",
                                "description": "Maximum emails with matching attachments",
                                "default": 10,
                            },
                        },
                        "required": ["search_text"],
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

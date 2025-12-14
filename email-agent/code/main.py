"""Main entry point for the email agent."""

import os
from dotenv import load_dotenv

from email_agent import (
    EmailAgent,
    authenticate_gmail,
    ElasticsearchEmailStore,
    GmailFetchTool,
    ElasticsearchSearchTool,
    ElasticsearchWriteTool,
    ConversationHistoryTool,
    SearchAttachmentsTool,
    CategorizeEmailsTool,
    PriorityInboxTool,
    fetch_and_index_all_emails,
)


def main():
    """Initialize and run the email agent."""

    # Load environment variables
    load_dotenv()

    # Configuration
    es_host = os.getenv("ES_HOST", "localhost")
    es_port = int(os.getenv("ES_PORT", "9200"))
    es_index = os.getenv("ES_INDEX_NAME", "emails")
    credentials_file = os.getenv("CREDENTIALS_FILE", "credentials.json")

    print("=" * 50)
    print("📧 Email Agent Initialization")
    print("=" * 50)

    # Initialize Gmail API
    print("\n🔐 Authenticating Gmail API...")
    try:
        gmail_service = authenticate_gmail(credentials_file)
        print("✓ Gmail API authenticated")
    except Exception as e:
        print(f"❌ Gmail authentication failed: {e}")
        return

    # Initialize Elasticsearch
    print(f"\n🔍 Connecting to Elasticsearch at {es_host}:{es_port}...")
    try:
        es_store = ElasticsearchEmailStore(
            es_host=es_host, es_port=es_port, index_name=es_index
        )
        print("✓ Elasticsearch connected")
    except Exception as e:
        print(f"❌ Elasticsearch connection failed: {e}")
        print("   Make sure Elasticsearch is running:")
        print(
            "   docker run -d --name elasticsearch -p 9200:9200 -p 9300:9300 -e discovery.type=single-node -e xpack.security.enabled=false docker.elastic.co/elasticsearch/elasticsearch:9.1.1"
        )
        return

    # Create tools
    print("\n🔧 Initializing tools...")
    gmail_tool = GmailFetchTool(gmail_service)
    search_tool = ElasticsearchSearchTool(es_store)
    write_tool = ElasticsearchWriteTool(es_store)
    conversation_tool = ConversationHistoryTool(es_store)
    attachment_tool = SearchAttachmentsTool(es_store)
    categorize_tool = CategorizeEmailsTool(es_store)
    priority_tool = PriorityInboxTool(es_store)
    print(
        "✓ Tools initialized: gmail_fetch, elasticsearch_search, conversation_history, search_attachments, elasticsearch_write, categorize_emails, priority_inbox"
    )

    # Create agent
    print("\n🤖 Creating email agent...")
    agent = EmailAgent(
        tools=[
            gmail_tool,
            search_tool,
            write_tool,
            conversation_tool,
            attachment_tool,
            categorize_tool,
            priority_tool,
        ]
    )
    print("✓ Agent ready")

    # Optional: Index emails on first run
    print("\n📨 Fetching and indexing emails...")
    try:
        indexed_emails = fetch_and_index_all_emails(
            gmail_service, es_store, max_emails=50
        )
        print(f"✓ Indexed {len(indexed_emails)} emails")
    except Exception as e:
        print(f"⚠️  Could not fetch emails: {e}")

    # Interactive chat loop
    print("\n" + "=" * 50)
    print("💬 Email Agent Ready - Chat with your emails!")
    print("Type 'quit' to exit")
    print("=" * 50 + "\n")

    while True:
        try:
            user_input = input("You: ").strip()

            if user_input.lower() in ["quit", "exit", "q"]:
                print("\n👋 Goodbye!")
                break

            if not user_input:
                continue

            print("\n🤖 Agent is thinking...\n")
            response = agent.chat(user_input)
            print(f"Agent: {response}\n")

        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}\n")


if __name__ == "__main__":
    main()

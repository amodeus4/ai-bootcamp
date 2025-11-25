# Email Agent

An intelligent email management agent powered by OpenAI's GPT-4, Gmail API, and Elasticsearch.

## Features

- 📧 Fetch emails from Gmail
- 🔍 Search emails in Elasticsearch
- 🤖 Natural language chat interface
- ✅ Organize and categorize emails
- 💾 Persistent email storage and indexing

## Prerequisites

- Python 3.12+
- `uv` package manager
- Gmail API credentials
- Elasticsearch instance (local or remote)

## Setup

### 1. Clone and Navigate

```bash
cd email-agent/code
```

### 2. Install Dependencies

```bash
make install
# or manually: uv sync
```

### 3. Configure Environment

```bash
make setup
# This creates .env from .env.example
```

Edit `.env` with your configuration:
- `CREDENTIALS_FILE`: Path to your Gmail API credentials.json
- `ES_HOST`: Elasticsearch host (default: localhost)
- `ES_PORT`: Elasticsearch port (default: 9200)
- `ES_INDEX_NAME`: Index name for emails (default: emails)
- `OPENAI_API_KEY`: Your OpenAI API key

### 4. Set Up Gmail API

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable the Gmail API
4. Create OAuth 2.0 credentials (Desktop app)
5. Download credentials as `credentials.json` and place in `email-agent/code/`

### 5. Start Elasticsearch

```bash
docker run -d \
  --name elasticsearch \
  -p 9200:9200 \
  -p 9300:9300 \
  -e discovery.type=single-node \
  -e xpack.security.enabled=false \
  docker.elastic.co/elasticsearch/elasticsearch:9.1.1
```

Or if you already have it running:
```bash
docker start elasticsearch
```

### 6. Run the Agent

```bash
make run
# or manually: uv run main.py
```

On first run, the agent will:
1. Authenticate with Gmail
2. Fetch and index your emails
3. Start an interactive chat session

## Usage

Once running, chat with your agent naturally:

```
You: Show my unread emails
Agent: [fetches and displays unread emails]

You: Find emails from john@example.com
Agent: [searches and returns matching emails]

You: What emails did I get about the project?
Agent: [searches for "project" and returns results]
```

## Project Structure

```
email-agent/code/
├── email_agent/           # Main package
│   ├── __init__.py
│   ├── agent.py           # EmailAgent class
│   ├── schemas.py         # Data models
│   ├── gmail_client.py    # Gmail API integration
│   ├── elasticsearch_store.py  # ES operations
│   └── tools/
│       └── __init__.py    # Tool definitions
├── tests/                 # Unit tests
├── main.py                # Entry point
├── pyproject.toml         # Dependencies
├── .env.example           # Environment template
├── Makefile               # Commands
└── README.md              # This file
```

## Development

### Run Tests

```bash
uv run pytest -s
```

### Clean Cache

```bash
make clean
```

## Troubleshooting

### Elasticsearch Connection Error

Make sure Elasticsearch is running:
```bash
docker ps | grep elasticsearch
```

If not running:
```bash
docker run -d --name elasticsearch -p 9200:9200 -p 9300:9300 -e discovery.type=single-node -e xpack.security.enabled=false docker.elastic.co/elasticsearch/elasticsearch:9.1.1
```

### Gmail Authentication Error

- Delete `token.pickle` to re-authenticate
- Ensure `credentials.json` is in the correct location
- Check that Gmail API is enabled in Google Cloud Console

### No Emails Indexed

- Check Gmail API credentials
- Verify network connectivity
- Check Elasticsearch is accessible

## Requirements

See `pyproject.toml` for full dependencies:
- google-auth-oauthlib
- google-api-python-client
- elasticsearch
- openai
- pydantic
- python-dotenv

## License

MIT

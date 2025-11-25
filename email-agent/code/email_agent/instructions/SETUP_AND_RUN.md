# Email Agent - Quick Start Guide

Your email agent project has been successfully converted to a structured project using `uv` and Python.

## 📁 Project Structure

```
email-agent/code/
├── email_agent/                 # Main package
│   ├── __init__.py             # Package exports
│   ├── agent.py                # EmailAgent class with LLM integration
│   ├── schemas.py              # EmailDocument and EmailAttachment models
│   ├── gmail_client.py         # Gmail API authentication & email parsing
│   ├── elasticsearch_store.py  # Elasticsearch operations & storage
│   └── tools/
│       └── __init__.py         # GmailFetchTool, SearchTool, WriteTool
├── tests/
│   ├── __init__.py
│   └── test_agent.py           # Unit tests
├── main.py                     # Entry point
├── pyproject.toml              # uv dependencies & configuration
├── .env.example                # Environment variables template
├── .gitignore                  # Git ignore rules
├── Makefile                    # Convenient commands
└── README.md                   # Full documentation
```

## 🚀 Installation & Setup

### Step 1: Navigate to the Project

```bash
cd /workspaces/ai-bootcamp/email-agent/code
```

### Step 2: Install Dependencies with uv

```bash
uv sync
```

This creates a `.venv` virtual environment and installs all dependencies.

### Step 3: Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your settings:
```env
CREDENTIALS_FILE=credentials.json
ES_HOST=localhost
ES_PORT=9200
ES_INDEX_NAME=emails
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o-mini
```

**Note:** `credentials.json` is already provided from your notebook.

### Step 4: Start Elasticsearch

```bash
docker run -d \
  --name elasticsearch \
  -p 9200:9200 \
  -p 9300:9300 \
  -e discovery.type=single-node \
  -e xpack.security.enabled=false \
  docker.elastic.co/elasticsearch/elasticsearch:9.1.1
```

Or restart if it already exists:
```bash
docker start elasticsearch
```

## ▶️ Running the Agent

### Start the Agent

```bash
make run
# or: uv run main.py
```

### First Run

On first run, the agent will:
1. Authenticate with Gmail (opens browser window)
2. Fetch and index your emails to Elasticsearch
3. Start an interactive chat session

### Chat with Your Agent

```
You: Show my unread emails
Agent: [displays unread emails with details]

You: Find emails from john@example.com
Agent: [searches Elasticsearch and returns results]

You: What emails did I receive about the project?
Agent: [searches for "project" and returns matching emails]

You: Mark important emails from manager
Agent: [uses tools to categorize emails]
```

Type `quit`, `exit`, or `q` to exit.

## 📋 Available Commands

```bash
make help          # Show all available commands
make install       # Install dependencies
make setup         # Create .env from template
make run           # Run the agent
make clean         # Clean cache files
```

## 🧪 Testing

```bash
uv run pytest -s
```

## 🔧 Key Components

### EmailAgent (`email_agent/agent.py`)
- Orchestrates tool calls via OpenAI's function calling
- Maintains conversation history
- Routes requests to appropriate tools

### Tools (`email_agent/tools/__init__.py`)
- **GmailFetchTool**: Fetches emails from Gmail
- **ElasticsearchSearchTool**: Searches indexed emails
- **ElasticsearchWriteTool**: Updates email metadata

### Gmail Client (`email_agent/gmail_client.py`)
- Handles OAuth2 authentication
- Parses Gmail API responses
- Fetches and indexes emails

### Elasticsearch Store (`email_agent/elasticsearch_store.py`)
- Manages email document storage
- Handles bulk indexing
- Provides search capabilities

### Schemas (`email_agent/schemas.py`)
- `EmailDocument`: Structured email representation
- `EmailAttachment`: Attachment metadata

## 🆘 Troubleshooting

### Elasticsearch Not Running
```bash
# Check if running
docker ps | grep elasticsearch

# Start it
docker start elasticsearch

# Or create fresh
docker run -d --name elasticsearch -p 9200:9200 -p 9300:9300 -e discovery.type=single-node -e xpack.security.enabled=false docker.elastic.co/elasticsearch/elasticsearch:9.1.1
```

### Gmail Authentication Issues
```bash
# Delete token and re-authenticate
rm token.pickle
make run
```

### "No module named 'email_agent'"
```bash
# Make sure you're in the right directory
cd /workspaces/ai-bootcamp/email-agent/code

# Reinstall
uv sync
```

### OpenAI API Key Error
```bash
# Update .env with your actual API key
nano .env  # or use your preferred editor
# Set: OPENAI_API_KEY=sk-...
```

## 📊 Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│  User Chat Interface (main.py)                          │
└────────────────┬────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────┐
│  EmailAgent (agent.py)                                  │
│  - Process user messages                                │
│  - Call OpenAI with function definitions                │
│  - Execute tool calls                                   │
└──┬──────────────────────────────────────────────────────┘
   │
   ├──────────────────────────────────────────────────────┐
   │                                                      │
   ▼                      ▼                      ▼        │
┌──────────────┐  ┌──────────────┐   ┌──────────────────┐ │
│Gmail Fetch   │  │Elasticsearch │   │Elasticsearch    │ │
│Tool          │  │Search Tool   │   │Write Tool       │ │
└──────┬───────┘  └──────┬───────┘   └────────┬─────────┘ │
       │                 │                    │          │
       ▼                 ▼                    ▼          │
    ┌──────────────────────────────────────────────────┐ │
    │  Gmail API      Elasticsearch Instance           │ │
    │  (Cloud)        (Docker localhost:9200)          │ │
    └──────────────────────────────────────────────────┘ │
       ▲                 ▲                    ▲          │
       └─────────────────┴────────────────────┘          │
                                                         │
                        EmailDocumentParser              │
                        Schemas                         │
                        (email_agent/*.py)              │
└────────────────────────────────────────────────────────┘
```

## 📚 Dependencies

See `pyproject.toml` for the full list. Key packages:

**Gmail Integration:**
- google-auth-oauthlib
- google-api-python-client

**Search & Storage:**
- elasticsearch

**AI/LLM:**
- openai
- pydantic

**Utilities:**
- python-dotenv
- PyPDF2, python-docx, openpyxl (for attachment processing)

## 🎯 Next Steps

1. ✅ Run `make install` to set up dependencies
2. ✅ Set up Elasticsearch with Docker
3. ✅ Update `.env` with your OpenAI API key
4. ✅ Run `make run` to start the agent
5. Start chatting with your emails!

## 📝 Notes

- The project structure follows the same patterns as week 3 code
- Uses Pydantic for data validation
- Elasticsearch for full-text search capabilities
- OpenAI function calling for intelligent tool routing
- Environment-based configuration for flexibility

---

**Your email agent is ready to go!** 🚀

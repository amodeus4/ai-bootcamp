# Quick Reference

## Installation (One-time)

```bash
cd /workspaces/ai-bootcamp/email-agent/code
uv sync                           # Install dependencies & create .venv
cp .env.example .env              # Create .env file
# Edit .env and add your OPENAI_API_KEY
```

## Start Elasticsearch (One-time per session)

```bash
docker start elasticsearch
# or if first time:
docker run -d --name elasticsearch -p 9200:9200 -p 9300:9300 \
  -e discovery.type=single-node -e xpack.security.enabled=false \
  docker.elastic.co/elasticsearch/elasticsearch:9.1.1
```

## Run the Agent

```bash
cd /workspaces/ai-bootcamp/email-agent/code
make run
```

## Available Make Commands

| Command | What it does |
|---------|------------|
| `make help` | Show all commands |
| `make install` | Install/update dependencies |
| `make setup` | Create .env file |
| `make run` | Start the agent |
| `make clean` | Clean cache files |

## Manual Commands (without make)

```bash
uv sync                    # Install dependencies
uv run main.py            # Run the agent
uv run pytest -s          # Run tests
```

## Environment Setup (.env)

```env
CREDENTIALS_FILE=credentials.json
ES_HOST=localhost
ES_PORT=9200
ES_INDEX_NAME=emails
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-4o-mini
LOG_LEVEL=INFO
```

## File Organization

- **email_agent/** - Main package
  - agent.py - EmailAgent with LLM
  - gmail_client.py - Gmail integration
  - elasticsearch_store.py - Data storage
  - schemas.py - Data models
  - tools/__init__.py - Tool definitions
- **tests/** - Unit tests
- **main.py** - Entry point

## Common Issues & Fixes

| Issue | Solution |
|-------|----------|
| "Elasticsearch not running" | `docker start elasticsearch` |
| "Gmail auth failed" | `rm token.pickle && make run` |
| "No module email_agent" | `cd .../email-agent/code && uv sync` |
| "OpenAI key error" | Add `OPENAI_API_KEY` to .env |

## Useful Links

- Gmail API: https://developers.google.com/gmail/api
- Elasticsearch: https://www.elastic.co/guide/en/elasticsearch/reference/current/index.html
- OpenAI API: https://platform.openai.com/docs/api-reference
- Pydantic: https://docs.pydantic.dev/

## Example Queries

```
"Show my unread emails"
"Find emails from john@example.com"
"Search for emails about the project from last week"
"How many emails do I have from HR?"
"Find emails with attachments"
"Show me important emails"
```

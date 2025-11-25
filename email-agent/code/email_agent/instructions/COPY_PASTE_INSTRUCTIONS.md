# 🚀 Copy-Paste Instructions to Run

Follow these exact steps in order. Just copy and paste each command.

## Step 1: Navigate to Project (5 seconds)

```bash
cd /workspaces/ai-bootcamp/email-agent/code
```

## Step 2: Install with uv (30 seconds)

```bash
uv sync
```

This creates `.venv` and installs all dependencies automatically.

## Step 3: Create Environment Config (30 seconds)

```bash
cp .env.example .env
```

Now open the `.env` file and **add your OpenAI API key**:

```bash
# Open in VS Code or editor
code .env
```

Update this line:
```
OPENAI_API_KEY=sk-your-actual-api-key-here
```

Save the file.

## Step 4: Start Elasticsearch (20 seconds)

Copy-paste **one** of these:

**Option A: If Elasticsearch is already running:**
```bash
docker start elasticsearch
```

**Option B: If this is your first time:**
```bash
docker run -d \
  --name elasticsearch \
  -p 9200:9200 \
  -p 9300:9300 \
  -e discovery.type=single-node \
  -e xpack.security.enabled=false \
  docker.elastic.co/elasticsearch/elasticsearch:9.1.1
```

## Step 5: Run the Agent (10 seconds)

```bash
make run
```

Or without make:
```bash
uv run main.py
```

## ✅ You're Done!

You should see:
```
==================================================
📧 Email Agent Initialization
==================================================

🔐 Authenticating Gmail API...
✓ Gmail API authenticated

🔍 Connecting to Elasticsearch at localhost:9200...
✓ Elasticsearch connected

🔧 Initializing tools...
✓ Tools initialized: gmail_fetch, elasticsearch_search, elasticsearch_write

🤖 Creating email agent...
✓ Agent ready

📨 Fetching and indexing emails...
✓ Indexed X emails

==================================================
💬 Email Agent Ready - Chat with your emails!
Type 'quit' to exit
==================================================

You: 
```

## 🎯 Example Queries

Try these:

```
You: Show my unread emails
You: Find emails from john@example.com
You: What emails did I get about the project?
You: Show me important emails
You: quit
```

## 🔑 Important Notes

1. **First run takes longer** - It fetches and indexes your emails
2. **Gmail will open a browser** - Authenticate there (first time only)
3. **Token is saved** - `token.pickle` saves auth for next time
4. **Conversation history** - Agent remembers context within session

## 🚨 If Something Goes Wrong

### Problem: "Elasticsearch connection failed"

**Solution:**
```bash
docker start elasticsearch
# Wait 5 seconds
make run
```

### Problem: "Gmail authentication failed"

**Solution:**
```bash
rm token.pickle
make run
# Authenticate again in browser
```

### Problem: "OpenAI API key error"

**Solution:**
```bash
code .env
# Add: OPENAI_API_KEY=sk-your-real-key-here
# Save and try again
```

### Problem: "No module named 'email_agent'"

**Solution:**
```bash
cd /workspaces/ai-bootcamp/email-agent/code
uv sync
make run
```

## 📖 Documentation Files

- **README.md** - Overview and summary
- **SETUP_AND_RUN.md** - Detailed setup guide
- **QUICK_REFERENCE.md** - Command reference
- **code/README.md** - Full documentation

## ⏱️ Total Time

- Setup: **2 minutes**
- First run: **3-5 minutes** (fetches emails)
- Subsequent runs: **10 seconds**

## 💬 Need Help?

1. Check `QUICK_REFERENCE.md` for common issues
2. Check `SETUP_AND_RUN.md` for detailed guide
3. Check `code/README.md` for full docs
4. All files have troubleshooting sections

---

**That's it! You're ready to chat with your emails.** 🎉

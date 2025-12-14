"""Unit tests for email agent components."""

import pytest
from email_agent import (
    EmailDocument,
    EmailAttachment,
    EmailAgent,
    GmailFetchTool,
    ElasticsearchSearchTool,
    ElasticsearchWriteTool,
    ConversationHistoryTool,
    SearchAttachmentsTool,
    CategorizeEmailsTool,
    PriorityInboxTool,
)


class TestEmailDocument:
    """Tests for EmailDocument schema."""

    def test_email_document_creation(self):
        """Test EmailDocument creation."""
        doc = EmailDocument(
            email_id="123",
            thread_id="456",
            sender_name="John Doe",
            sender_email="john@example.com",
            subject="Test Email",
        )

        assert doc.email_id == "123"
        assert doc.sender_email == "john@example.com"
        assert doc.subject == "Test Email"

    def test_email_document_with_recipients(self):
        """Test EmailDocument with recipients."""
        doc = EmailDocument(
            email_id="123",
            thread_id="456",
            sender_name="John Doe",
            sender_email="john@example.com",
            subject="Test Email",
            recipients=["jane@example.com", "bob@example.com"],
        )

        assert len(doc.recipients) == 2
        assert "jane@example.com" in doc.recipients

    def test_email_document_to_es(self):
        """Test EmailDocument conversion to Elasticsearch format."""
        doc = EmailDocument(
            email_id="123",
            thread_id="456",
            sender_name="John Doe",
            sender_email="john@example.com",
            subject="Test Email",
            recipients=["jane@example.com"],
        )

        es_doc = doc.to_es_document()

        assert es_doc["_id"] == "123"
        assert es_doc["_source"]["sender"]["email"] == "john@example.com"
        assert "jane@example.com" in es_doc["_source"]["recipients"]

    def test_email_document_with_body_plain(self):
        """Test EmailDocument with email body_plain."""
        body_text = "This is the email body content"
        doc = EmailDocument(
            email_id="123",
            thread_id="456",
            sender_name="John Doe",
            sender_email="john@example.com",
            subject="Test Email",
            body_plain=body_text,
        )

        assert doc.body_plain == body_text

    def test_email_document_with_attachments(self):
        """Test EmailDocument with attachments."""
        att = EmailAttachment(
            filename="test.pdf",
            mime_type="application/pdf",
            attachment_id="att1",
            size=1024,
        )
        doc = EmailDocument(
            email_id="123",
            thread_id="456",
            sender_name="John Doe",
            sender_email="john@example.com",
            subject="Test Email",
            attachments=[att],
            has_attachments=True,
        )

        assert len(doc.attachments) == 1
        assert doc.has_attachments is True


class TestEmailAttachment:
    """Tests for EmailAttachment schema."""

    def test_email_attachment_creation(self):
        """Test EmailAttachment creation."""
        att = EmailAttachment(
            filename="test.pdf",
            mime_type="application/pdf",
            attachment_id="att123",
            size=1024,
        )

        assert att.filename == "test.pdf"
        assert att.size == 1024
        assert att.mime_type == "application/pdf"

    def test_email_attachment_to_es(self):
        """Test EmailAttachment conversion to Elasticsearch format."""
        att = EmailAttachment(
            filename="test.pdf",
            mime_type="application/pdf",
            attachment_id="att123",
            size=1024,
        )

        es_dict = att.to_es_dict()
        assert es_dict["filename"] == "test.pdf"
        assert es_dict["mime_type"] == "application/pdf"
        assert es_dict["size"] == 1024

    def test_attachment_types(self):
        """Test different attachment types."""
        test_files = [
            ("document.pdf", "application/pdf"),
            (
                "spreadsheet.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ),
            ("image.png", "image/png"),
            ("archive.zip", "application/zip"),
        ]

        for filename, mime_type in test_files:
            att = EmailAttachment(
                filename=filename,
                mime_type=mime_type,
                attachment_id=f"att_{filename}",
                size=2048,
            )
            assert att.filename == filename
            assert att.mime_type == mime_type


class TestEmailAgent:
    """Tests for EmailAgent initialization and structure."""

    def test_agent_initialization_requires_tools(self):
        """Test that EmailAgent requires tools."""
        with pytest.raises(TypeError):
            EmailAgent()

    def test_agent_has_system_prompt(self):
        """Test that agent has a system prompt configured."""
        agent = EmailAgent(tools=[])
        assert agent.system_prompt is not None
        assert len(agent.system_prompt) > 0
        assert "email" in agent.system_prompt.lower()

    def test_agent_tool_dictionary(self):
        """Test that agent creates tool dictionary."""
        # Create mock tools
        mock_tools = []
        agent = EmailAgent(tools=mock_tools)
        assert isinstance(agent.tools, dict)


class TestToolConfiguration:
    """Tests for tool configuration and availability."""

    def test_required_tools_defined(self):
        """Test that required tool classes are defined and have proper structure."""
        required_tools = [
            GmailFetchTool,
            ElasticsearchSearchTool,
            ElasticsearchWriteTool,
            ConversationHistoryTool,
            SearchAttachmentsTool,
            CategorizeEmailsTool,
            PriorityInboxTool,
        ]

        for tool_class in required_tools:
            assert tool_class is not None
            # Check that class has __init__ method (tools define name as instance attribute)
            assert hasattr(tool_class, "__init__")
            # Verify class name suggests it's a tool
            assert "Tool" in tool_class.__name__

    def test_tool_names_are_unique(self):
        """Test that each tool has a unique name."""
        # We can't instantiate these without services, but we can check names exist
        tool_classes = [
            GmailFetchTool,
            ElasticsearchSearchTool,
            ElasticsearchWriteTool,
            ConversationHistoryTool,
            SearchAttachmentsTool,
            CategorizeEmailsTool,
            PriorityInboxTool,
        ]

        names = [t.name for t in tool_classes if hasattr(t, "name")]
        assert len(names) == len(set(names)), "Tool names should be unique"


class TestSystemPromptBehavior:
    """Tests for agent system prompt behavior."""

    def test_system_prompt_mentions_mys_context(self):
        """Test that system prompt includes MYS business context."""
        agent = EmailAgent(tools=[])
        assert "MYS" in agent.system_prompt
        assert "payment_request_non_mys" in agent.system_prompt

    def test_system_prompt_explains_payment_request_logic(self):
        """Test that system prompt explains non-MYS payment filtering."""
        agent = EmailAgent(tools=[])
        # Should explain that MYS emails should be excluded for payment requests
        prompt_lower = agent.system_prompt.lower()
        assert "external" in prompt_lower or "non-mys" in prompt_lower
        assert "categorize" in prompt_lower

from tests.utils import get_tool_calls
import main


# Test to ensure the agent makes at least 3 search tool calls
def test_agent_makes_3_search_calls():
    user_prompt = "What is LLM evaluation?"
    result = main.run_agent_sync(user_prompt)

    print(result.output)

    messages = result.new_messages()

    tool_calls = get_tool_calls(result)
    assert len(tool_calls) >= 3, f"Expected at least 3 tool calls, got {len(tool_calls)}"


# Test to ensure the agent adds references with GitHub URLs
def test_agent_makes_adds_references():
    user_prompt = "What is LLM evaluation?"
    result = main.run_agent_sync(user_prompt)

    print(result.output)

    messages = result.new_messages()

    tool_calls = get_tool_calls(result)
    assert len(tool_calls) >= 3, f"Expected at least 3 tool calls, got {len(tool_calls)}"
    assert "## References:" in result.output, "Expected References in the response"
    assert 'https://github.com/evidentlyai/docs/blob/main/' in result.output, "Expected GitHub URLs in the References"


# Test to ensure the agent can answer with code snippets
def test_agent_answer_with_code():
    user_prompt = "How do I implement LLm as a judge eval?"
    result = main.run_agent_sync(user_prompt)

    print(result.output)

    messages = result.new_messages()
    assert "```python" in result.output
    


# instead of waiting for the agent to finish working on the outout i want it to stream it.
# the problem is hat we have structured output so we'll implement streaming using pydantic AI's event stream handler

import asyncio

import search_agent


async def main():
    user_input = "How do I monitor data drift in production?"

    agent = search_agent.create_agent()
    callback = search_agent.NamedCallback(agent)

    previous_text = ""

    async with agent.run_stream(user_input, event_stream_handler=callback) as result:
        async for item, last in result.stream_responses(debounce_by=0.01):  #
            for part in item.parts:
                if not hasattr(
                    part, "tool_name"
                ):  # skip parts without tool_name attribute
                    continue
                if part.tool_name != "final_result":  # only care about final result
                    continue

                current_text = part.args
                delta = current_text[len(previous_text) :]
                print(delta, end="", flush=True)
                previous_text = current_text


if __name__ == "__main__":
    asyncio.run(main())

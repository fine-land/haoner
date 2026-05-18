"""Test script for the agent loop."""

import asyncio
import logging
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(level=logging.INFO)

from agent.agent_loop import HermesAgentLoop
from tools.model_tools import get_tool_definitions


class MockLLMClient:
    """Mock LLM client for testing."""
    
    def __init__(self, responses):
        self.responses = responses
        self.index = 0
        self.chat = type('obj', (object,), {
            'completions': type('obj', (object,), {
                'create': self._create_completion
            })
        })
    
    async def _create_completion(self, **kwargs):
        if self.index >= len(self.responses):
            return MockLLMClient.MockResponse([
                MockLLMClient.MockChoice(
                    MockLLMClient.MockMessage("I've completed the task!")
                )
            ])
        
        response = self.responses[self.index]
        self.index += 1
        
        if response.get("tool_calls"):
            tool_calls = [
                MockLLMClient.MockToolCall(tc["name"], tc["arguments"])
                for tc in response["tool_calls"]
            ]
            return MockLLMClient.MockResponse([
                MockLLMClient.MockChoice(
                    MockLLMClient.MockMessage(None, tool_calls)
                )
            ])
        else:
            return MockLLMClient.MockResponse([
                MockLLMClient.MockChoice(
                    MockLLMClient.MockMessage(response.get("content", ""))
                )
            ])
    
    class MockToolCall:
        def __init__(self, name, arguments):
            self.function = type('obj', (object,), {
                'name': name,
                'arguments': arguments
            })
            self.id = f"call_{hash(name)}"
    
    class MockMessage:
        def __init__(self, content, tool_calls=None):
            self.content = content
            self.tool_calls = tool_calls
            self.reasoning = None
    
    class MockChoice:
        def __init__(self, message):
            self.message = message
    
    class MockResponse:
        def __init__(self, choices):
            self.choices = choices


async def test_agent_loop():
    """Test the agent loop with mock LLM responses."""
    # Load tools
    from tools import file_tools, terminal_tool
    
    # Get tool definitions
    tools = get_tool_definitions()
    tool_names = {t["function"]["name"] for t in tools}
    
    print(f"Available tools: {tool_names}")
    
    # Mock responses - simulate a conversation where agent lists directory
    mock_responses = [
        {
            "tool_calls": [
                {
                    "name": "terminal",
                    "arguments": '{"command": "ls -la /home/zzh/hermes/my_hermes"}'
                }
            ]
        },
        {
            "content": "I've listed the directory contents. The task is complete!"
        }
    ]
    
    # Create mock client
    client = MockLLMClient(mock_responses)
    
    # Create agent loop
    agent = HermesAgentLoop(
        client=client,
        tool_schemas=tools,
        valid_tool_names=tool_names,
        max_turns=5,
    )
    
    # Initial messages
    messages = [
        {"role": "system", "content": "You are a helpful assistant. Use tools as needed."},
        {"role": "user", "content": "List the files in /home/zzh/hermes/my_hermes directory"},
    ]
    
    # Run agent
    result = await agent.run(messages)
    
    print(f"\n=== Agent Result ===")
    print(f"Turns used: {result.turns_used}")
    print(f"Finished naturally: {result.finished_naturally}")
    
    print("\n=== Conversation History ===")
    for i, msg in enumerate(result.messages):
        role = msg["role"]
        content = msg.get("content", "")[:200] if msg.get("content") else ""
        tool_calls = msg.get("tool_calls", [])
        
        print(f"\n[{i+1}] {role}:")
        if tool_calls:
            for tc in tool_calls:
                print(f"  Tool call: {tc['function']['name']}")
                print(f"  Args: {tc['function']['arguments']}")
        elif content:
            print(f"  Content: {content}...")


if __name__ == "__main__":
    asyncio.run(test_agent_loop())
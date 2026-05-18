#!/usr/bin/env python3
"""Test context compression module."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import asyncio
from agent.context_compression import (
    apply_tool_result_budget,
    snip_compact_if_needed,
    microcompact,
    apply_context_collapse,
    autocompact,
    apply_all_compressions
)


async def test_compressions():
    """Test all compression techniques."""
    # Create test messages
    test_messages = [
        {"role": "user", "content": "Hello, what's the weather today?"},
        {"role": "assistant", "content": "I'll check the weather for you."},
        {"role": "tool", "content": '{"command": "weather", "result": "Sunny, 25C" * 200}'},  # Long tool result
        {"role": "assistant", "content": "The weather is sunny with 25 degrees Celsius."},
        {"role": "user", "content": "Thanks! What about tomorrow?"},
        {"role": "assistant", "content": "Let me check tomorrow's forecast."},
        {"role": "tool", "content": '{"command": "forecast", "result": "Cloudy, 22C"}'},
        {"role": "assistant", "content": "Tomorrow will be cloudy with 22 degrees."},
        # Add some redundant messages for testing
        {"role": "assistant", "content": "The weather is nice today. The weather is pleasant."},
        {"role": "assistant", "content": "The weather is nice today. The weather is pleasant."},
    ]
    
    print("=== Testing Context Compression ===")
    print(f"Original messages: {len(test_messages)}")
    original_chars = sum(len(str(m.get('content', ''))) for m in test_messages)
    print(f"Original chars: {original_chars}\n")
    
    # Test 1: Tool Result Budget
    print("1. Tool Result Budget Trimming")
    messages1 = apply_tool_result_budget(test_messages.copy(), max_tool_result_chars=500)
    chars1 = sum(len(str(m.get('content', ''))) for m in messages1)
    print(f"   Result: {len(messages1)} messages, {chars1} chars")
    print(f"   Saved: {original_chars - chars1} chars\n")
    
    # Test 2: History Snip
    print("2. History Snip Compact")
    messages2, applied = snip_compact_if_needed(test_messages.copy(), max_messages=5)
    print(f"   Applied: {applied}")
    print(f"   Result: {len(messages2)} messages\n")
    
    # Test 3: Microcompact
    print("3. Microcompact")
    messages3, saved = microcompact(test_messages.copy())
    print(f"   Saved: {saved} chars\n")
    
    # Test 4: Context Collapse
    print("4. Context Collapse")
    messages4, merged = await apply_context_collapse(test_messages.copy())
    print(f"   Merged: {merged} message pairs")
    print(f"   Result: {len(messages4)} messages\n")
    
    # Test 5: Autocompact
    print("5. Autocompact")
    messages5, applied = await autocompact(test_messages.copy(), max_total_chars=500)
    print(f"   Applied: {applied}")
    print(f"   Result: {len(messages5)} messages\n")
    
    # Test All Together
    print("=== All Compressions Combined ===")
    result = await apply_all_compressions(test_messages.copy())
    final_chars = sum(len(str(m.get('content', ''))) for m in result['messages'])
    print(f"Final messages: {len(result['messages'])}")
    print(f"Final chars: {final_chars}")
    print(f"Total saved: {original_chars - final_chars} chars")
    print("\nStats:", result['stats'])


if __name__ == "__main__":
    asyncio.run(test_compressions())

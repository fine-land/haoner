"""
Prompt Builder - 构建完整的 Agent 提示词

包含:
1. System Prompt - 角色定义和核心指令 (adapted from Claude Code)
2. Tool Information - 工具使用说明
3. Format Instructions - 输出格式要求
"""

import json
import os
from typing import List, Dict, Any, Optional


class PromptBuilder:
    """构建 Agent 提示词的工具类"""

    def __init__(self):
        self.system_prompt = self._get_default_system_prompt()
        self.tool_instructions = ""

    def _get_default_system_prompt(self) -> str:
        """获取默认的系统提示词 - adapted from Claude Code"""
        from .system_prompt import get_system_prompt_string
        return get_system_prompt_string(os.getcwd())

    def build_tool_instructions(self, tools: List[Dict[str, Any]]) -> str:
        """构建工具使用说明"""
        if not tools:
            return ""

        instructions = "\n## 可用工具\n\n"

        for tool in tools:
            func = tool.get("function", {})
            name = func.get("name", "")
            desc = func.get("description", "")
            params = func.get("parameters", {}).get("properties", {})

            instructions += f"### {name}\n"
            instructions += f"- 描述: {desc}\n"

            if params:
                instructions += "- 参数:\n"
                for param_name, param_info in params.items():
                    param_type = param_info.get("type", "string")
                    param_desc = param_info.get("description", "")
                    instructions += f"  - {param_name} ({param_type}): {param_desc}\n"

            instructions += "\n"

        return instructions

    def build_prompt(
        self,
        user_message: str,
        tools: List[Dict[str, Any]] = None,
        history: List[Dict[str, Any]] = None,
        system_prompt: str = None
    ) -> List[Dict[str, Any]]:
        """
        构建完整的提示词消息列表

        Args:
            user_message: 当前用户消息
            tools: 可用工具列表
            history: 对话历史
            system_prompt: 自定义系统提示词

        Returns:
            完整的消息列表，可直接传递给 LLM API
        """
        messages = []

        # 1. System Message（系统消息）
        sys_msg = {
            "role": "system",
            "content": system_prompt or self.system_prompt
        }

        # 添加工具说明到系统消息
        if tools:
            sys_msg["content"] += self.build_tool_instructions(tools)

        messages.append(sys_msg)

        # 2. Conversation History（对话历史）
        if history:
            messages.extend(history)

        # 3. Current User Message（当前用户消息）
        messages.append({
            "role": "user",
            "content": user_message
        })

        return messages

    def build_tool_result_message(self, tool_name: str, result: str, tool_call_id: str) -> Dict[str, Any]:
        """构建工具执行结果消息"""
        return {
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": result
        }

    def build_assistant_message(self, content: str, tool_calls: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """构建 Assistant 响应消息"""
        msg = {
            "role": "assistant",
            "content": content
        }
        if tool_calls:
            msg["tool_calls"] = tool_calls
        return msg


# 全局实例
prompt_builder = PromptBuilder()


def build_prompt(
    user_message: str,
    tools: List[Dict[str, Any]] = None,
    history: List[Dict[str, Any]] = None,
    system_prompt: str = None
) -> List[Dict[str, Any]]:
    """便捷函数：构建完整提示词"""
    return prompt_builder.build_prompt(user_message, tools, history, system_prompt)

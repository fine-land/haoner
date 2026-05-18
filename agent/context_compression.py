"""
Context Compression Module - Five compression techniques from Claude Code

Implements:
1. Tool Result Budget Trimming - 限制工具结果长度
2. History Snip Compact - 裁剪历史消息
3. Microcompact - 微压缩（移除冗余空白）
4. Context Collapse - 上下文坍缩（合并相似消息）
5. Autocompact - 自动压缩（总结长对话）
"""

import asyncio
import json
import logging
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)


def apply_tool_result_budget(
    messages: List[Dict[str, Any]],
    max_tool_result_chars: int = 4000,
    tool_result_truncation_suffix: str = "\n[TRUNCATED]"
) -> List[Dict[str, Any]]:
    """
    1. Tool Result Budget Trimming - 限制工具结果长度
    
    对工具调用的结果进行裁剪，避免过长的输出占据太多上下文。
    """
    compressed = []
    for msg in messages:
        if msg.get('role') == 'tool':
            content = msg.get('content', "")
            if len(content) > max_tool_result_chars:
                msg = msg.copy()
                msg['content'] = content[:max_tool_result_chars] + tool_result_truncation_suffix
                logger.debug(f"Trimmed tool result from {len(content)} to {max_tool_result_chars} chars")
        compressed.append(msg)
    return compressed


def snip_compact_if_needed(
    messages: List[Dict[str, Any]],
    max_messages: int = 50,
    keep_recent: int = 20
) -> Tuple[List[Dict[str, Any]], bool]:
    """
    2. History Snip Compact - 裁剪历史消息
    
    如果消息数量超过阈值，保留最近的消息并对早期消息进行采样。
    """
    if len(messages) <= max_messages:
        return messages, False
    
    logger.debug(f"Snipping messages: {len(messages)} -> {max_messages}")
    
    # 保留最近的消息
    recent = messages[-keep_recent:]
    
    # 对早期消息进行采样
    early = messages[:-keep_recent]
    sample_rate = max(1, len(early) // (max_messages - keep_recent))
    sampled_early = early[::sample_rate]
    
    return sampled_early + recent, True


def microcompact(
    messages: List[Dict[str, Any]]
) -> Tuple[List[Dict[str, Any]], int]:
    """
    3. Microcompact - 微压缩
    
    移除多余的空白字符和空行，进行轻量级压缩。
    """
    original_chars = sum(len(str(m.get('content', ''))) for m in messages)
    
    compressed = []
    for msg in messages:
        if 'content' in msg and msg['content']:
            msg = msg.copy()
            # 移除多余空白
            content = msg['content']
            if isinstance(content, str):
                # 压缩连续空白
                lines = content.split('\n')
                # 移除空行和多余空格
                compressed_lines = [
                    line.strip() for line in lines 
                    if line.strip()
                ]
                msg['content'] = '\n'.join(compressed_lines)
        compressed.append(msg)
    
    new_chars = sum(len(str(m.get('content', ''))) for m in compressed)
    saved_chars = original_chars - new_chars
    
    logger.debug(f"Microcompact saved {saved_chars} chars")
    return compressed, saved_chars


async def apply_context_collapse(
    messages: List[Dict[str, Any]],
    similarity_threshold: float = 0.7
) -> Tuple[List[Dict[str, Any]], int]:
    """
    4. Context Collapse - 上下文坍缩
    
    合并相似的连续消息，减少冗余。
    """
    if len(messages) < 2:
        return messages, 0
    
    collapsed = []
    collapsed_count = 0
    
    i = 0
    while i < len(messages):
        current = messages[i]
        
        # 只合并 assistant 角色的连续相似消息
        if current.get('role') == 'assistant' and i + 1 < len(messages):
            next_msg = messages[i + 1]
            
            if next_msg.get('role') == 'assistant':
                current_content = str(current.get('content', ''))
                next_content = str(next_msg.get('content', ''))
                
                # 计算相似度（简化版本：基于共同词比例）
                similarity = _calculate_similarity(current_content, next_content)
                
                if similarity >= similarity_threshold:
                    # 合并两条消息
                    merged = current.copy()
                    merged['content'] = current_content + "\n" + next_content
                    collapsed.append(merged)
                    collapsed_count += 1
                    i += 2  # 跳过下一条
                    continue
        
        collapsed.append(current)
        i += 1
    
    logger.debug(f"Context collapse merged {collapsed_count} message pairs")
    return collapsed, collapsed_count


def _calculate_similarity(str1: str, str2: str) -> float:
    """计算两个字符串的相似度（简化版本）"""
    words1 = set(str1.lower().split())
    words2 = set(str2.lower().split())
    
    if not words1 and not words2:
        return 1.0
    if not words1 or not words2:
        return 0.0
    
    intersection = words1 & words2
    union = words1 | words2
    
    return len(intersection) / len(union)


async def autocompact(
    messages: List[Dict[str, Any]],
    max_total_chars: int = 16000,
    summary_ratio: float = 0.3,
    client = None
) -> Tuple[List[Dict[str, Any]], bool]:
    """
    5. Autocompact - 自动压缩
    
    当上下文过长时，对早期消息进行总结。
    """
    total_chars = sum(len(str(m.get('content', ''))) for m in messages)
    
    if total_chars <= max_total_chars:
        return messages, False
    
    logger.debug(f"Autocompact needed: {total_chars} > {max_total_chars}")
    
    # 计算需要总结的消息数量
    chars_to_remove = total_chars - max_total_chars
    chars_per_summary = int(chars_to_remove * summary_ratio)
    
    # 找到需要总结的早期消息
    early_messages = []
    early_chars = 0
    
    for msg in messages:
        if msg.get('role') == 'assistant':
            early_messages.append(msg)
            early_chars += len(str(msg.get('content', '')))
            if early_chars >= chars_per_summary:
                break
    
    if not early_messages:
        return messages, False
    
    # 生成总结（Mock 模式或真实总结）
    summary_content = await _generate_summary(early_messages, client)
    
    # 替换早期消息为总结
    summary_msg = {
        "role": "system",
        "content": f"Previous conversation summary:\n{summary_content}",
        "is_summary": True
    }
    
    # 找到第一个 assistant 消息的位置
    first_assistant_idx = next(
        (i for i, m in enumerate(messages) if m.get('role') == 'assistant'),
        0
    )
    
    compressed = [summary_msg] + messages[first_assistant_idx + len(early_messages):]
    
    logger.debug(f"Autocompact replaced {len(early_messages)} messages with summary")
    return compressed, True


async def _generate_summary(messages: List[Dict[str, Any]], client = None) -> str:
    """生成消息总结"""
    # 如果有真实 LLM 客户端，使用它生成总结
    if client and not hasattr(client, 'use_mock'):
        # 真实总结逻辑（简化）
        content = "\n".join(str(m.get('content', '')) for m in messages)
        return f"Summary of {len(messages)} messages: {content[:200]}..."
    
    # Mock 总结
    content = "\n".join(str(m.get('content', '')) for m in messages)
    lines = content.split('\n')[:3]  # 取前3行作为简化总结
    return "\n".join(lines) + ("..." if len(content) > 200 else "")


async def apply_all_compressions(
    messages: List[Dict[str, Any]],
    client = None,
    config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    应用所有压缩技术（按顺序）
    
    Args:
        messages: 原始消息列表
        client: LLM 客户端（用于 autocompact）
        config: 压缩配置
    
    Returns:
        {
            'messages': 压缩后的消息,
            'stats': 压缩统计信息
        }
    """
    # 默认配置
    cfg = config or {}
    stats = {
        'original_count': len(messages),
        'original_chars': sum(len(str(m.get('content', ''))) for m in messages),
        'tool_budget_applied': False,
        'snip_applied': False,
        'microcompact_saved': 0,
        'collapse_merged': 0,
        'autocompact_applied': False,
    }
    
    # 1. 工具结果预算裁剪
    messages = apply_tool_result_budget(
        messages,
        max_tool_result_chars=cfg.get('max_tool_result_chars', 4000)
    )
    stats['tool_budget_applied'] = True
    
    # 2. 历史裁剪
    messages, stats['snip_applied'] = snip_compact_if_needed(
        messages,
        max_messages=cfg.get('max_messages', 50),
        keep_recent=cfg.get('keep_recent', 20)
    )
    
    # 3. 微压缩
    messages, stats['microcompact_saved'] = microcompact(messages)
    
    # 4. 上下文坍缩
    if cfg.get('enable_context_collapse', True):
        messages, stats['collapse_merged'] = await apply_context_collapse(
            messages,
            similarity_threshold=cfg.get('similarity_threshold', 0.7)
        )
    
    # 5. 自动压缩
    if cfg.get('enable_autocompact', True):
        messages, stats['autocompact_applied'] = await autocompact(
            messages,
            max_total_chars=cfg.get('max_total_chars', 16000),
            client=client
        )
    
    stats['final_count'] = len(messages)
    stats['final_chars'] = sum(len(str(m.get('content', ''))) for m in messages)
    stats['total_saved_chars'] = stats['original_chars'] - stats['final_chars']
    
    logger.info(f"Compression completed: {stats['original_chars']} -> {stats['final_chars']} chars, saved {stats['total_saved_chars']}")
    
    return {
        'messages': messages,
        'stats': stats
    }

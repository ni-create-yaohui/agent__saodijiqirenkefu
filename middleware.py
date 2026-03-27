# -*- coding: utf-8 -*-
"""
中间件模块 - 工具监控、日志记录、提示词切换
"""

import time
from typing import Callable, Optional
from project.prompt_loader import load_system_prompts, load_report_prompts
from langchain.agents import AgentState
from langchain.agents.middleware import wrap_tool_call, before_model, dynamic_prompt, ModelRequest
from langchain.tools.tool_node import ToolCallRequest
from langchain_core.messages import ToolMessage
from langgraph.runtime import Runtime
from langgraph.types import Command
from project.logger_handler import logger


@wrap_tool_call
def monitor_tool(
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], ToolMessage | Command],
) -> ToolMessage | Command:
    """
    工具执行监控中间件
    记录工具调用信息、执行时间，并记录到文件
    """
    tool_name = request.tool_call['name']
    tool_args = request.tool_call['args']

    logger.info(f"[Tool Monitor] 执行工具: {tool_name}")
    logger.info(f"[Tool Monitor] 参数: {tool_args}")

    start_time = time.time()
    try:
        result = handler(request)
        execution_time = int((time.time() - start_time) * 1000)
        logger.info(f"[Tool Monitor] {tool_name} 执行成功, 耗时 {execution_time}ms")

        # 报告生成场景标记
        if tool_name == "fill_context_for_report":
            request.runtime.context["report"] = True

        # 记录工具调用日志
        _save_tool_log(
            session_id=request.runtime.context.get("session_id"),
            user_id=request.runtime.context.get("user_id"),
            tool_name=tool_name,
            tool_args=tool_args,
            tool_result=result.content[:500] if hasattr(result, 'content') else str(result)[:500],
            execution_time_ms=execution_time,
            success=True
        )

        return result
    except Exception as e:
        execution_time = int((time.time() - start_time) * 1000)
        logger.error(f"[Tool Monitor] {tool_name} 执行失败: {e}")

        # 记录失败日志
        _save_tool_log(
            session_id=request.runtime.context.get("session_id"),
            user_id=request.runtime.context.get("user_id"),
            tool_name=tool_name,
            tool_args=tool_args,
            tool_result=str(e),
            execution_time_ms=execution_time,
            success=False
        )
        raise e


def _save_tool_log(session_id: str, user_id: str, tool_name: str,
                   tool_args: dict, tool_result: str, execution_time_ms: int, success: bool):
    """保存工具调用日志到文件"""
    try:
        from services.storage_service import tool_log_service
        tool_log_service.log_tool_call(
            session_id=session_id,
            user_id=user_id,
            tool_name=tool_name,
            tool_args=tool_args,
            tool_result=tool_result,
            execution_time_ms=execution_time_ms,
            success=success
        )
    except Exception as e:
        logger.warning(f"保存工具日志失败: {e}")


@before_model
def log_before_model(state: AgentState, runtime: Runtime):
    """
    模型调用前日志中间件
    """
    messages = state.get('messages', [])
    logger.info(f"[Model] 即将调用模型，消息数: {len(messages)}")

    if messages:
        last_msg = messages[-1]
        msg_type = type(last_msg).__name__
        content_preview = last_msg.content[:100] if hasattr(last_msg, 'content') else str(last_msg)[:100]
        logger.debug(f"[Model] 最后消息: {msg_type} | {content_preview}...")

    return None


@dynamic_prompt
def report_prompt_switch(request: ModelRequest):
    """
    动态提示词切换中间件
    根据上下文自动切换报告生成提示词
    """
    is_report = request.runtime.context.get("report", False)

    if is_report:
        logger.info("[Prompt] 切换到报告生成提示词")
        return load_report_prompts()

    return load_system_prompts()
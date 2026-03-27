# -*- coding: utf-8 -*-
"""
ReAct 智能体 - 支持多工具调用和会话管理
"""

from langchain.agents import create_agent
from model.factory import chat_model
from project.prompt_loader import load_system_prompts
from agent.tools.agent_tools import (
    rag_summarize,
    get_user_id,
    fetch_external_data,
    fill_context_for_report
)
from agent.tools.web_tools import (
    get_weather,
    web_search,
    get_user_location,
    fetch_webpage,
    get_current_datetime
)
from agent.tools.business_tools import (
    recommend_product,
    diagnose_fault,
    maintenance_advice,
    query_usage_record,
    get_current_month,
    query_order,
    consumable_reminder
)
from agent.tools.middleware import monitor_tool, log_before_model, report_prompt_switch


class ReactAgent:
    """
    ReAct 智能体类
    支持多工具自动调用、会话管理、报告生成
    """

    def __init__(self, session_id: str = None, user_id: str = None):
        self.session_id = session_id
        self.user_id = user_id
        self.agent = create_agent(
            model=chat_model,
            system_prompt=load_system_prompts(),
            tools=[
                # === 网络工具 ===
                get_weather,              # 天气查询
                web_search,               # 网络搜索
                get_user_location,        # IP定位
                fetch_webpage,            # 网页抓取
                get_current_datetime,     # 当前时间

                # === 客服业务工具 ===
                recommend_product,        # 产品推荐
                diagnose_fault,           # 故障诊断
                maintenance_advice,       # 保养建议
                query_usage_record,       # 使用记录查询
                get_current_month,        # 获取当前月份
                query_order,              # 订单查询
                consumable_reminder,      # 耗材提醒

                # === 数据工具 ===
                rag_summarize,            # RAG知识检索
                get_user_id,              # 获取用户ID
                fetch_external_data,      # 外部数据获取
                fill_context_for_report,  # 报告上下文注入
            ],
            middleware=[monitor_tool, log_before_model, report_prompt_switch],
        )

    def set_context(self, session_id: str = None, user_id: str = None):
        """设置会话上下文"""
        if session_id:
            self.session_id = session_id
        if user_id:
            self.user_id = user_id

    def execute_stream(self, query: str):
        """
        流式执行智能体

        Args:
            query: 用户查询

        Yields:
            文本片段
        """
        input_dict = {
            "messages": [
                {"role": "user", "content": query},
            ]
        }

        # 传递上下文信息
        context = {
            "report": False,
            "session_id": self.session_id,
            "user_id": self.user_id
        }

        for chunk in self.agent.stream(input_dict, stream_mode="values", context=context):
            latest_message = chunk["messages"][-1]
            if latest_message.content:
                yield latest_message.content.strip() + "\n"

    def execute(self, query: str) -> str:
        """
        同步执行智能体

        Args:
            query: 用户查询

        Returns:
            完整响应文本
        """
        result = ""
        for chunk in self.execute_stream(query):
            result += chunk
        return result


# 默认智能体实例
default_agent = ReactAgent()


if __name__ == '__main__':
    agent = ReactAgent()

    # 测试产品推荐
    print("=== 测试产品推荐 ===")
    for chunk in agent.execute_stream("推荐一款3000元左右的扫地机器人，家里有猫"):
        print(chunk, end="", flush=True)

    print("\n\n=== 测试故障诊断 ===")
    for chunk in agent.execute_stream("我的扫地机器人噪音很大，怎么办？"):
        print(chunk, end="", flush=True)
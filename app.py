# -*- coding: utf-8 -*-
"""
智扫通机器人智能客服 - Streamlit 主应用
支持会话管理、历史记录、多用户等功能
"""

import streamlit as st
from datetime import datetime
from agent.react_agent import ReactAgent
from services.storage_service import (
    session_service,
    chat_history_service,
    report_service,
    user_service,
    feedback_service
)

# 页面配置
st.set_page_config(
    page_title="智扫通 - 机器人智能客服",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义CSS
st.markdown("""
<style>
    .stChatMessage {
        padding: 10px;
        border-radius: 10px;
        margin-bottom: 10px;
    }
    .stChatMessage[data-testid="user-message"] {
        background-color: #e3f2fd;
    }
    .stChatMessage[data-testid="assistant-message"] {
        background-color: #f5f5f5;
    }
    .session-item {
        padding: 10px;
        border-radius: 8px;
        margin-bottom: 5px;
        cursor: pointer;
        border: 1px solid #e0e0e0;
    }
    .session-item:hover {
        background-color: #f0f0f0;
    }
    .session-item.active {
        background-color: #e3f2fd;
        border-color: #2196f3;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)


def init_session_state():
    """初始化会话状态"""
    if "agent" not in st.session_state:
        st.session_state["agent"] = None
    if "current_session_id" not in st.session_state:
        st.session_state["current_session_id"] = None
    if "user_id" not in st.session_state:
        st.session_state["user_id"] = None
    if "messages" not in st.session_state:
        st.session_state["messages"] = []
    if "page" not in st.session_state:
        st.session_state["page"] = "chat"


def get_or_create_agent():
    """获取或创建智能体实例"""
    if st.session_state["agent"] is None:
        st.session_state["agent"] = ReactAgent(
            session_id=st.session_state.get("current_session_id"),
            user_id=st.session_state.get("user_id")
        )
    return st.session_state["agent"]


def create_new_session():
    """创建新会话"""
    session = session_service.create_session(
        user_id=st.session_state.get("user_id"),
        session_name=None
    )
    st.session_state["current_session_id"] = session["session_id"]
    st.session_state["messages"] = []

    # 更新智能体上下文
    if st.session_state["agent"]:
        st.session_state["agent"].set_context(
            session_id=session["session_id"],
            user_id=st.session_state.get("user_id")
        )

    return session


def load_session_history(session_id: str):
    """加载会话历史"""
    history = chat_history_service.get_history(session_id)
    st.session_state["messages"] = []

    for msg in history:
        st.session_state["messages"].append({
            "role": msg["role"],
            "content": msg["content"]
        })


def save_message(role: str, content: str, tool_name: str = None):
    """保存消息到历史记录"""
    session_id = st.session_state.get("current_session_id")
    if session_id:
        chat_history_service.save_message(session_id, role, content, tool_name)


# 初始化
init_session_state()


# ==================== 侧边栏 ====================
with st.sidebar:
    st.title("🤖 智扫通客服")
    st.caption("扫地机器人专业客服系统")

    # 用户ID输入
    user_id_input = st.text_input(
        "用户ID",
        value=st.session_state.get("user_id", ""),
        placeholder="输入您的用户ID（如：1001）"
    )

    if user_id_input != st.session_state.get("user_id"):
        st.session_state["user_id"] = user_id_input
        if user_id_input:
            user_service.get_or_create_user(user_id_input)

    st.divider()

    # 页面导航
    page = st.radio(
        "功能导航",
        ["💬 智能对话", "📋 我的报告", "⚙️ 设置"],
        label_visibility="collapsed"
    )

    st.divider()

    # 会话管理
    if page == "💬 智能对话":
        st.subheader("会话管理")

        if st.button("➕ 新建会话", use_container_width=True):
            create_new_session()
            st.rerun()

        # 会话列表
        sessions = session_service.list_sessions(
            user_id=st.session_state.get("user_id"),
            limit=10
        )

        if sessions:
            st.caption("历史会话")
            for session in sessions:
                col1, col2 = st.columns([4, 1])
                with col1:
                    session_label = session.get("session_name", "未命名")
                    msg_count = session.get("message_count", 0)
                    if st.button(
                        f"📝 {session_label} ({msg_count}条)",
                        key=f"session_{session['session_id']}",
                        use_container_width=True
                    ):
                        st.session_state["current_session_id"] = session["session_id"]
                        load_session_history(session["session_id"])
                        st.rerun()

                with col2:
                    if st.button("🗑️", key=f"del_{session['session_id']}"):
                        session_service.delete_session(session["session_id"])
                        if st.session_state["current_session_id"] == session["session_id"]:
                            st.session_state["current_session_id"] = None
                            st.session_state["messages"] = []
                        st.rerun()


# ==================== 主内容区 ====================

if page == "💬 智能对话":
    # 对话页面
    st.title("💬 智能对话")

    # 显示当前会话信息
    if st.session_state.get("current_session_id"):
        session = session_service.get_session(st.session_state["current_session_id"])
        if session:
            st.caption(f"当前会话: {session.get('session_name', '未命名')} | 消息数: {session.get('message_count', 0)}")

    # 显示对话历史
    for message in st.session_state["messages"]:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # 用户输入
    if prompt := st.chat_input("请输入您的问题..."):
        # 确保有会话
        if not st.session_state.get("current_session_id"):
            create_new_session()

        # 显示用户消息
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state["messages"].append({"role": "user", "content": prompt})

        # 保存用户消息
        save_message("user", prompt)

        # 获取智能体响应
        agent = get_or_create_agent()

        with st.chat_message("assistant"):
            response_placeholder = st.empty()
            full_response = ""

            try:
                for chunk in agent.execute_stream(prompt):
                    full_response += chunk
                    response_placeholder.markdown(full_response + "▌")
                response_placeholder.markdown(full_response)
            except Exception as e:
                full_response = f"抱歉，处理您的请求时出现错误：{str(e)}"
                response_placeholder.markdown(full_response)

        # 保存助手响应
        st.session_state["messages"].append({"role": "assistant", "content": full_response})
        save_message("assistant", full_response)

        # 反馈按钮
        col1, col2, col3 = st.columns([1, 1, 4])
        with col1:
            if st.button("👍 有帮助", key=f"positive_{len(st.session_state['messages'])}"):
                feedback_service.submit_feedback(
                    user_id=st.session_state.get("user_id"),
                    session_id=st.session_state.get("current_session_id"),
                    feedback_type="positive",
                    content=full_response[:200],
                    rating=5
                )
                st.toast("感谢您的反馈！")
        with col2:
            if st.button("👎 需改进", key=f"negative_{len(st.session_state['messages'])}"):
                feedback_service.submit_feedback(
                    user_id=st.session_state.get("user_id"),
                    session_id=st.session_state.get("current_session_id"),
                    feedback_type="negative",
                    content=full_response[:200],
                    rating=2
                )
                st.toast("感谢反馈，我们会持续改进！")


elif page == "📋 我的报告":
    # 报告页面
    st.title("📋 我的分析报告")

    user_id = st.session_state.get("user_id")

    if not user_id:
        st.info("请先在侧边栏输入您的用户ID")
    else:
        # 搜索框
        search_query = st.text_input("搜索报告", placeholder="输入关键词...")

        # 获取报告列表
        if search_query:
            reports = report_service.search_reports(search_query)
        else:
            reports = report_service.list_reports(user_id=user_id, limit=20)

        if reports:
            for report in reports:
                with st.expander(
                    f"📄 {report.get('title', '未命名')} - {report.get('month', report.get('created_at', '')[:10])}",
                    expanded=False
                ):
                    st.markdown(f"**报告ID:** {report.get('report_id')}")
                    st.markdown(f"**类型:** {report.get('report_type', 'usage')}")
                    st.markdown(f"**创建时间:** {report.get('created_at')}")

                    content = report.get('content', '')
                    if len(content) > 500:
                        st.markdown(content[:500] + "...")
                        if st.button("查看完整报告", key=f"view_{report.get('report_id')}"):
                            st.markdown(content)
                    else:
                        st.markdown(content)

                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("🗑️ 删除", key=f"del_report_{report.get('report_id')}"):
                            report_service.delete_report(report.get('report_id'))
                            st.rerun()
        else:
            st.info("暂无报告记录。您可以在对话中请求生成使用报告。")


elif page == "⚙️ 设置":
    # 设置页面
    st.title("⚙️ 设置")

    user_id = st.session_state.get("user_id")

    if user_id:
        user = user_service.get_user(user_id)
        if user:
            st.subheader("用户信息")
            st.write(f"**用户ID:** {user.get('user_id')}")
            st.write(f"**用户名:** {user.get('username', '未设置')}")
            st.write(f"**创建时间:** {user.get('created_at', '未知')}")
            st.write(f"**会话数:** {user.get('session_count', 0)}")

            # 用户名设置
            new_username = st.text_input("修改用户名", value=user.get('username', ''))
            if st.button("保存"):
                user_service.update_user(user_id, username=new_username)
                st.success("用户名已更新")

    st.divider()

    # 快捷功能
    st.subheader("快捷功能")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🗑️ 清空当前会话历史"):
            session_id = st.session_state.get("current_session_id")
            if session_id:
                chat_history_service.clear_history(session_id)
                st.session_state["messages"] = []
                st.success("历史已清空")
                st.rerun()
            else:
                st.warning("请先选择一个会话")

    with col2:
        if st.button("📊 查看使用统计"):
            st.info("功能开发中...")

    st.divider()

    # 关于
    st.subheader("关于")
    st.info("""
    **智扫通机器人智能客服系统**

    基于大语言模型的智能客服，为您提供：
    - 产品咨询与推荐
    - 故障诊断与解决方案
    - 使用报告生成
    - 保养维护建议

    版本: 2.0.0
    """)


# 页脚
st.divider()
st.caption("智扫通机器人智能客服 © 2025 | 基于大语言模型技术")
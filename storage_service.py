# -*- coding: utf-8 -*-
"""
数据存储服务 - 基于本地 JSON 文件的数据持久化
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from project.path_tool import get_abs_path
from project.logger_handler import logger


class FileStorageService:
    """文件存储服务基类"""

    def __init__(self, data_dir: str, filename: str):
        self.data_dir = Path(get_abs_path(data_dir))
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.filepath = self.data_dir / filename
        self._ensure_file()

    def _ensure_file(self):
        """确保文件存在"""
        if not self.filepath.exists():
            self._save({})

    def _load(self) -> Dict:
        """加载数据"""
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载数据失败: {e}")
            return {}

    def _save(self, data: Dict):
        """保存数据"""
        try:
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存数据失败: {e}")


class UserService(FileStorageService):
    """用户服务 - 管理用户信息"""

    def __init__(self):
        super().__init__("data", "users.json")

    def get_user(self, user_id: str) -> Optional[Dict]:
        """获取用户信息"""
        data = self._load()
        return data.get(user_id)

    def get_or_create_user(self, user_id: str, username: str = None) -> Dict:
        """获取或创建用户"""
        data = self._load()
        if user_id not in data:
            data[user_id] = {
                "user_id": user_id,
                "username": username or f"用户{user_id}",
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "last_login_at": None,
                "session_count": 0,
                "report_count": 0,
                "device_info": None
            }
            self._save(data)
        return data[user_id]

    def update_user(self, user_id: str, **kwargs) -> bool:
        """更新用户信息"""
        data = self._load()
        if user_id in data:
            data[user_id].update(kwargs)
            data[user_id]["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self._save(data)
            return True
        return False

    def list_users(self) -> List[Dict]:
        """获取所有用户列表"""
        data = self._load()
        return list(data.values())


class SessionService(FileStorageService):
    """会话服务 - 管理对话会话"""

    def __init__(self):
        super().__init__("data/sessions", "sessions_index.json")

    def create_session(self, user_id: str = None, session_name: str = None) -> Dict:
        """创建新会话"""
        import uuid
        session_id = str(uuid.uuid4())[:8].upper()

        data = self._load()
        session = {
            "session_id": session_id,
            "user_id": user_id,
            "session_name": session_name or f"会话 {datetime.now().strftime('%m%d-%H%M')}",
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "last_message_at": None,
            "message_count": 0,
            "is_active": True
        }
        data[session_id] = session
        self._save(data)

        # 创建会话消息文件
        self._init_session_messages(session_id)

        return session

    def _init_session_messages(self, session_id: str):
        """初始化会话消息文件"""
        messages_file = self.data_dir / f"session_{session_id}.json"
        with open(messages_file, 'w', encoding='utf-8') as f:
            json.dump({"messages": []}, f, ensure_ascii=False, indent=2)

    def get_session(self, session_id: str) -> Optional[Dict]:
        """获取会话信息"""
        data = self._load()
        return data.get(session_id)

    def update_session(self, session_id: str, **kwargs) -> bool:
        """更新会话信息"""
        data = self._load()
        if session_id in data:
            data[session_id].update(kwargs)
            self._save(data)
            return True
        return False

    def list_sessions(self, user_id: str = None, limit: int = 20) -> List[Dict]:
        """获取会话列表"""
        data = self._load()
        sessions = list(data.values())

        if user_id:
            sessions = [s for s in sessions if s.get("user_id") == user_id]

        # 按最后消息时间排序
        sessions.sort(key=lambda x: x.get("last_message_at") or "0", reverse=True)
        return sessions[:limit]

    def delete_session(self, session_id: str) -> bool:
        """删除会话"""
        data = self._load()
        if session_id in data:
            del data[session_id]
            self._save(data)

            # 删除消息文件
            messages_file = self.data_dir / f"session_{session_id}.json"
            if messages_file.exists():
                messages_file.unlink()

            return True
        return False


class ChatHistoryService(FileStorageService):
    """对话历史服务 - 管理消息记录"""

    def __init__(self):
        self.sessions_dir = Path(get_abs_path("data/sessions"))
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

    def _get_session_file(self, session_id: str) -> Path:
        """获取会话消息文件路径"""
        return self.sessions_dir / f"session_{session_id}.json"

    def save_message(self, session_id: str, role: str, content: str, tool_name: str = None) -> bool:
        """保存消息"""
        messages_file = self._get_session_file(session_id)

        if not messages_file.exists():
            return False

        try:
            with open(messages_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            message = {
                "role": role,
                "content": content,
                "tool_name": tool_name,
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            data["messages"].append(message)

            with open(messages_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            # 更新会话索引
            self._update_session_stats(session_id)

            return True
        except Exception as e:
            logger.error(f"保存消息失败: {e}")
            return False

    def _update_session_stats(self, session_id: str):
        """更新会话统计"""
        from services.storage_service import SessionService
        session_service = SessionService()

        messages_file = self._get_session_file(session_id)
        if messages_file.exists():
            with open(messages_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            session_service.update_session(
                session_id,
                message_count=len(data.get("messages", [])),
                last_message_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )

    def get_history(self, session_id: str, limit: int = 50) -> List[Dict]:
        """获取对话历史"""
        messages_file = self._get_session_file(session_id)

        if not messages_file.exists():
            return []

        try:
            with open(messages_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            messages = data.get("messages", [])
            return messages[-limit:]
        except Exception as e:
            logger.error(f"获取历史失败: {e}")
            return []

    def clear_history(self, session_id: str) -> bool:
        """清空对话历史"""
        messages_file = self._get_session_file(session_id)

        try:
            with open(messages_file, 'w', encoding='utf-8') as f:
                json.dump({"messages": []}, f, ensure_ascii=False, indent=2)

            from services.storage_service import SessionService
            session_service = SessionService()
            session_service.update_session(session_id, message_count=0, last_message_at=None)

            return True
        except Exception as e:
            logger.error(f"清空历史失败: {e}")
            return False


class ReportService(FileStorageService):
    """报告服务 - 管理分析报告"""

    def __init__(self):
        super().__init__("data/reports", "reports_index.json")

    def create_report(self, user_id: str, title: str, content: str,
                      report_type: str = "usage", month: str = None,
                      session_id: str = None, summary: str = None) -> Dict:
        """创建报告"""
        import uuid
        report_id = f"R{datetime.now().strftime('%Y%m%d')}{str(uuid.uuid4())[:4].upper()}"

        data = self._load()
        report = {
            "report_id": report_id,
            "user_id": user_id,
            "session_id": session_id,
            "title": title,
            "report_type": report_type,
            "month": month,
            "content": content,
            "summary": summary or content[:200] + "...",
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        data[report_id] = report
        self._save(data)

        return report

    def get_report(self, report_id: str) -> Optional[Dict]:
        """获取报告"""
        data = self._load()
        return data.get(report_id)

    def list_reports(self, user_id: str = None, report_type: str = None,
                     limit: int = 20) -> List[Dict]:
        """获取报告列表"""
        data = self._load()
        reports = list(data.values())

        if user_id:
            reports = [r for r in reports if r.get("user_id") == user_id]
        if report_type:
            reports = [r for r in reports if r.get("report_type") == report_type]

        reports.sort(key=lambda x: x.get("created_at", "0"), reverse=True)
        return reports[:limit]

    def delete_report(self, report_id: str) -> bool:
        """删除报告"""
        data = self._load()
        if report_id in data:
            del data[report_id]
            self._save(data)
            return True
        return False

    def search_reports(self, query: str) -> List[Dict]:
        """搜索报告"""
        data = self._load()
        results = []
        query_lower = query.lower()

        for report in data.values():
            title = report.get("title", "").lower()
            content = report.get("content", "").lower()
            summary = report.get("summary", "").lower()

            if query_lower in title or query_lower in content or query_lower in summary:
                results.append(report)

        return results


class ToolLogService(FileStorageService):
    """工具调用日志服务"""

    def __init__(self):
        super().__init__("data/logs", "tool_logs.json")

    def log_tool_call(self, session_id: str, user_id: str, tool_name: str,
                      tool_args: Dict, tool_result: str, execution_time_ms: int,
                      success: bool = True):
        """记录工具调用"""
        data = self._load()

        log_entry = {
            "id": str(len(data) + 1),
            "session_id": session_id,
            "user_id": user_id,
            "tool_name": tool_name,
            "tool_args": tool_args,
            "tool_result": tool_result[:500] if tool_result else "",
            "execution_time_ms": execution_time_ms,
            "success": success,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        data[log_entry["id"]] = log_entry
        self._save(data)

    def get_logs(self, session_id: str = None, tool_name: str = None,
                 limit: int = 50) -> List[Dict]:
        """获取日志"""
        data = self._load()
        logs = list(data.values())

        if session_id:
            logs = [l for l in logs if l.get("session_id") == session_id]
        if tool_name:
            logs = [l for l in logs if l.get("tool_name") == tool_name]

        logs.sort(key=lambda x: x.get("created_at", "0"), reverse=True)
        return logs[:limit]


class FeedbackService(FileStorageService):
    """用户反馈服务"""

    def __init__(self):
        super().__init__("data", "feedback.json")

    def submit_feedback(self, user_id: str, session_id: str,
                        feedback_type: str, content: str, rating: int = None):
        """提交反馈"""
        import uuid
        data = self._load()

        feedback = {
            "feedback_id": str(uuid.uuid4())[:8].upper(),
            "user_id": user_id,
            "session_id": session_id,
            "feedback_type": feedback_type,
            "content": content,
            "rating": rating,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        data[feedback["feedback_id"]] = feedback
        self._save(data)

        return feedback

    def list_feedback(self, limit: int = 50) -> List[Dict]:
        """获取反馈列表"""
        data = self._load()
        feedbacks = list(data.values())
        feedbacks.sort(key=lambda x: x.get("created_at", "0"), reverse=True)
        return feedbacks[:limit]


# 创建全局服务实例
user_service = UserService()
session_service = SessionService()
chat_history_service = ChatHistoryService()
report_service = ReportService()
tool_log_service = ToolLogService()
feedback_service = FeedbackService()

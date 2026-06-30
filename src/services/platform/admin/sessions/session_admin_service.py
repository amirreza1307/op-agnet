from __future__ import annotations

import copy
from typing import Any, Optional

from api.errors import NotFoundError
from database.repositories.agno.agno_session_repo import AgnoSessionRepo
from setup.translator import trans


class SessionAdminService:
    @staticmethod
    def _serialize(session: Any) -> dict[str, Any]:
        if hasattr(session, "model_dump"):
            return session.model_dump(mode="json")
        if hasattr(session, "to_dict"):
            return session.to_dict()
        if isinstance(session, dict):
            return session
        return {}

    @classmethod
    def _merge_runs(cls, runs: list[dict]) -> list[dict]:
        if not isinstance(runs, list) or not runs:
            return []
        all_messages: list[dict] = []
        seen_keys: set[Any] = set()
        for run in runs:
            if not isinstance(run, dict):
                continue
            messages = run.get("messages") or []
            if not isinstance(messages, list):
                continue
            for msg in messages:
                if not isinstance(msg, dict):
                    continue
                msg["is_answer_msg"] = bool(
                    (msg.get("content") is not None and msg.get("role") == "assistant")
                    or msg.get("stop_after_tool_call")
                )

                msg_id = msg.get("id")
                key: Any = msg_id if msg_id else ("by_content", msg.get("role"), msg.get("content"))
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                all_messages.append(msg)

        all_messages.sort(key=lambda m: (m.get("created_at") is None, m.get("created_at")))
        base_run = copy.deepcopy(runs[0]) if isinstance(runs[0], dict) else {}
        base_run["messages"] = all_messages
        return [base_run]

    @classmethod
    def _summary(cls, session: Any) -> dict[str, Any]:
        data = cls._serialize(session)
        runs = data.get("runs") or []
        return {
            "session_id": data.get("session_id"),
            "user_id": data.get("user_id"),
            "workflow_id": data.get("workflow_id"),
            "team_id": data.get("team_id"),
            "agent_id": data.get("agent_id"),
            "session_type": data.get("session_type") or "",
            "created_at": data.get("created_at"),
            "updated_at": data.get("updated_at"),
            "run_count": len(runs) if isinstance(runs, list) else 0,
            "has_summary": bool(data.get("summary")),
        }

    @classmethod
    def _detail(cls, session: Any) -> dict[str, Any]:
        data = cls._serialize(session)
        runs = data.get("runs") or []
        merged_runs = cls._merge_runs(runs)
        return {
            **cls._summary(data),
            "session_data": data.get("session_data"),
            "agent_data": data.get("agent_data"),
            "summary": data.get("summary"),
            "runs": merged_runs or [],
            "metadata": data.get("metadata"),
            "workflow_data": data.get("workflow_data"),
            "team_data": data.get("team_data"),
            "x_ref": data.get("x_ref"),
        }

    @classmethod
    async def list_recent(
        cls,
        *,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        team_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        session_type: Optional[str] = None,
        limit: int = 20,
        page: int = 1,
    ) -> dict[str, Any]:
        sessions, total = await AgnoSessionRepo.list_recent(
            user_id=user_id,
            agent_id=agent_id,
            team_id=team_id,
            workflow_id=workflow_id,
            session_type=session_type,
            limit=limit,
            page=page,
        )
        return {
            "items": [cls._summary(session) for session in sessions],
            "total": total,
            "page": page,
            "limit": limit,
        }

    @classmethod
    async def get_detail(
        cls,
        session_id: str,
        *,
        user_id: Optional[str] = None,
    ) -> dict[str, Any]:
        session = await AgnoSessionRepo.find_by_id(session_id, user_id=user_id)
        if not session:
            raise NotFoundError(trans("errors.platform.admin.agno_session_not_found", session_id=session_id))
        return cls._detail(session)

from fastapi import APIRouter

from api.controllers.v1.admin.session_controller import SessionController
from api.response_models.v1.admin.admin_response_models import (
    AgnoSessionDetailResponseModel,
    AgnoSessionListResponseModel,
)


router = APIRouter(prefix="/v1/admin", tags=["Platform Admin - Sessions"])


@router.get("/sessions", response_model=AgnoSessionListResponseModel)
async def list_recent_sessions(
    user_id: str | None = None,
    agent_id: str | None = None,
    team_id: str | None = None,
    workflow_id: str | None = None,
    session_type: str | None = None,
    limit: int = 20,
    page: int = 1,
):
    return await SessionController().list_recent(
        user_id=user_id,
        agent_id=agent_id,
        team_id=team_id,
        workflow_id=workflow_id,
        session_type=session_type,
        limit=limit,
        page=page,
    )


@router.get("/sessions/{session_id}", response_model=AgnoSessionDetailResponseModel)
async def get_session_detail(session_id: str, user_id: str | None = None):
    return await SessionController().detail(session_id, user_id=user_id)


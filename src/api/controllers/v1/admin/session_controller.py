from api.controllers.controller_abstract import ControllerAbstract
from services.platform.admin.sessions.session_admin_service import SessionAdminService


class SessionController(ControllerAbstract):

    async def list_recent(
        self,
        user_id: str | None = None,
        agent_id: str | None = None,
        team_id: str | None = None,
        workflow_id: str | None = None,
        session_type: str | None = None,
        limit: int = 20,
        page: int = 1,
    ):
        return await SessionAdminService.list_recent(
            user_id=user_id,
            agent_id=agent_id,
            team_id=team_id,
            workflow_id=workflow_id,
            session_type=session_type,
            limit=limit,
            page=page,
        )

    async def detail(self, session_id: str, user_id: str | None = None):
        return await SessionAdminService.get_detail(session_id, user_id=user_id)


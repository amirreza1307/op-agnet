from datetime import datetime


class AgentApiKeyPrincipal:
    __slots__ = ("key_id", "node_id", "key_prefix", "expires_at")

    def __init__(
        self,
        *,
        key_id: int,
        node_id: int,
        key_prefix: str,
        expires_at: datetime,
    ):
        self.key_id = key_id
        self.node_id = node_id
        self.key_prefix = key_prefix
        self.expires_at = expires_at

from typing import ClassVar

from basalam.backbone_orm import ModelSchemaAbstract


class LlmRequestLogSchema(ModelSchemaAbstract):
    ID: ClassVar[str] = 'id'
    SCOPE: ClassVar[str] = 'scope'
    MODEL: ClassVar[str] = 'model'
    MESSAGES: ClassVar[str] = 'messages'
    RESPONSE: ClassVar[str] = 'response'
    PROMPT_TOKENS: ClassVar[str] = 'prompt_tokens'
    COMPLETION_TOKENS: ClassVar[str] = 'completion_tokens'
    TOTAL_TOKENS: ClassVar[str] = 'total_tokens'
    COST_USD: ClassVar[str] = 'cost_usd'
    CREATED_AT: ClassVar[str] = 'created_at'

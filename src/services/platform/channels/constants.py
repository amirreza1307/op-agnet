from enum import Enum


class ChannelType(str, Enum):
    TELEGRAM = "telegram"
    BALE = "bale"


DEFAULT_API_BASE_URLS = {
    ChannelType.TELEGRAM.value: "https://api.telegram.org",
    ChannelType.BALE.value: "https://tapi.bale.ai",
}

SUPPORTED_CHANNEL_TYPES = frozenset(DEFAULT_API_BASE_URLS)

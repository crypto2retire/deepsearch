from app.skills.base import Skill
from app.skills.general import GENERAL
from app.skills.market_research import MARKET_RESEARCH
from app.skills.stock_crypto import STOCK_CRYPTO
from app.skills.social_content import SOCIAL_CONTENT
from app.skills.youtube_video import YOUTUBE_VIDEO
from app.skills.coding import CODING

ALL_SKILLS: list[Skill] = [
    GENERAL,
    MARKET_RESEARCH,
    STOCK_CRYPTO,
    SOCIAL_CONTENT,
    YOUTUBE_VIDEO,
    CODING,
]

SKILL_MAP: dict[str, Skill] = {s.id: s for s in ALL_SKILLS}


def get_skill(skill_id: str) -> Skill:
    return SKILL_MAP.get(skill_id, GENERAL)

from dataclasses import dataclass
from ashredis import RecordBase, MISSING
from typing import Optional

@dataclass
class Url(RecordBase):
    id: str 
    short_id: Optional[str] = MISSING  # короткий ID как строка
    original_url: Optional[str] = MISSING  # URL как строка

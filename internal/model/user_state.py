from datetime import datetime
from dataclasses import dataclass


@dataclass
class UserState:
    id: int
    tg_chat_id: int
    tg_username: str
    created_at: datetime

    @classmethod
    def serialize(cls, rows) -> list:
        return [
            cls(
                id=row.id,
                tg_chat_id=row.tg_chat_id,
                tg_username=row.tg_username,
                created_at=row.created_at,
            )
            for row in rows
        ]


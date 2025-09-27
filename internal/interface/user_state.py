from typing import Protocol
from abc import abstractmethod

from internal import model


class IStateService(Protocol):

    @abstractmethod
    async def create_state(self, tg_chat_id: int, tg_username: str) -> int: pass

    @abstractmethod
    async def state_by_id(self, tg_chat_id: int) -> list[model.UserState]: pass

    @abstractmethod
    async def change_user_state(
            self,
            state_id: int,
    ) -> None: pass


class IStateRepo(Protocol):

    @abstractmethod
    async def create_state(self, tg_chat_id: int, tg_username: str) -> int: pass

    @abstractmethod
    async def state_by_id(self, tg_chat_id: int) -> list[model.UserState]: pass

    @abstractmethod
    async def change_user_state(
            self,
            state_id: int,
    ) -> None: pass

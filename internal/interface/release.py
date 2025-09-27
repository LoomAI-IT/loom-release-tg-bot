from abc import abstractmethod
from typing import Protocol

from fastapi.responses import JSONResponse

from internal import model
from internal.controller.http.handler.release.model import *


class IReleaseController(Protocol):
    @abstractmethod
    async def create_release(self, body: CreateReleaseBody) -> JSONResponse:
        pass

    @abstractmethod
    async def update_release(self, body: UpdateReleaseBody) -> JSONResponse:
        pass


class IReleaseService(Protocol):
    @abstractmethod
    async def create_release(
            self,
            service_name: str,
            release_version: str,
            initiated_by: str,
            github_run_id: str,
            github_action_link: str,
            github_ref: str
    ) -> int:
        pass

    @abstractmethod
    async def update_release(
            self,
            release_id: int,
            status: model.ReleaseStatus
    ) -> None:
        pass


class IReleaseRepo(Protocol):
    @abstractmethod
    async def create_release(
            self,
            service_name: str,
            release_version: str,
            status: model.ReleaseStatus,
            initiated_by: str,
            github_run_id: str,
            github_action_link: str,
            github_ref: str
    ) -> int:
        pass

    @abstractmethod
    async def update_release(
            self,
            release_id: int,
            status: model.ReleaseStatus,
    ) -> None:
        pass

from abc import abstractmethod
from typing import Protocol


class IGutHubClient(Protocol):
    @abstractmethod
    async def trigger_workflow(
            self,
            owner: str,
            repo: str,
            workflow_id: str,
            ref: str = "main",
            inputs: dict = None
    ) -> None: pass

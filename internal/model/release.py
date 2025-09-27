from datetime import datetime
from dataclasses import dataclass
from enum import Enum


class ReleaseStatus(Enum):
    INITIATED = "initiated"
    BUILDING = "building"

    MANUAL_TESTING = "manual_testing"
    MANUAL_TEST_PASSED = "manual_test_passed"
    MANUAL_TEST_FAILED = "manual_test_failed"

    DEPLOYING = "deploying"
    DEPLOYED = "deployed"
    FAILED = "failed"
    ROLLBACK = "rollback"
    CANCELLED = "cancelled"


@dataclass
class Release:
    id: int
    service_name: str
    release_version: str
    status: ReleaseStatus

    initiated_by: str
    github_run_id: str
    github_action_link: str
    github_ref: str

    created_at: datetime
    started_at: datetime
    completed_at: datetime

    @classmethod
    def serialize(cls, rows) -> list:
        return [
            cls(
                id=row.id,
                service_name=row.service_name,
                release_version=row.release_version,
                status=ReleaseStatus(row.status),
                initiated_by=row.initiated_by,
                github_run_id=row.github_run_id,
                github_action_link=row.github_action_link,
                github_ref=row.github_ref,
                created_at=row.created_at,
                started_at=row.started_at,
                completed_at=row.completed_at,
            )
            for row in rows
        ]
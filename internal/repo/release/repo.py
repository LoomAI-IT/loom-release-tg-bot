from opentelemetry.trace import SpanKind, Status, StatusCode

from internal.repo.release.query import *
from internal import model
from internal import interface


class ReleaseRepo(interface.IReleaseRepo):
    def __init__(self, tel: interface.ITelemetry, db: interface.IDB):
        self.db = db
        self.tracer = tel.tracer()

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
        with self.tracer.start_as_current_span(
                "ReleaseRepo.create_release",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                args = {
                    "service_name": service_name,
                    "release_version": release_version,
                    "status": status,
                    "initiated_by": initiated_by,
                    "github_run_id": github_run_id,
                    "github_action_link": github_action_link,
                    "github_ref": github_ref,
                }
                release_id = await self.db.insert(create_release, args)

                span.set_status(StatusCode.OK)
                return release_id

            except Exception as err:
                span.record_exception(err)
                span.set_status(StatusCode.ERROR, str(err))
                raise err

    async def update_release(
            self,
            release_id: int,
            status: model.ReleaseStatus,
    ) -> None:
        with self.tracer.start_as_current_span(
                "StateRepo.change_status",
                kind=SpanKind.INTERNAL,
                attributes={
                    "release_id": release_id,
                }
        ) as span:
            try:
                update_fields = []
                args: dict = {'release_id': release_id}

                if not update_fields:
                    span.set_status(Status(StatusCode.OK))
                    return

                if status is not None:
                    update_fields.append("status = :status")
                    args['status'] = status

                query = f"""
                UPDATE releases 
                SET {', '.join(update_fields)}
                WHERE id = :release_id;
                """

                await self.db.update(query, args)
                span.set_status(StatusCode.OK)

            except Exception as err:
                span.record_exception(err)
                span.set_status(StatusCode.ERROR, str(err))
                raise

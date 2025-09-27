from opentelemetry.trace import SpanKind, Status, StatusCode

from internal import interface, model


class ReleaseService(interface.IReleaseService):
    def __init__(
            self,
            tel: interface.ITelemetry,
            release_repo: interface.IReleaseRepo
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.release_repo = release_repo

    async def create_release(
            self,
            service_name: str,
            release_version: str,
            initiated_by: str,
            github_run_id: str,
            github_action_link: str,
            github_ref: str
    ) -> int:
        with self.tracer.start_as_current_span(
                "ReleaseService.create_release",
                kind=SpanKind.INTERNAL,
                attributes={
                    "service_name": service_name,
                    "release_version": release_version,
                    "initiated_by": initiated_by,
                    "github_run_id": github_run_id,
                    "github_ref": github_ref,
                }
        ) as span:
            try:
                release_id = await self.release_repo.create_release(
                    service_name=service_name,
                    release_version=release_version,
                    status=model.ReleaseStatus.INITIATED,
                    initiated_by=initiated_by,
                    github_run_id=github_run_id,
                    github_action_link=github_action_link,
                    github_ref=github_ref
                )

                span.set_status(Status(StatusCode.OK))
                return release_id

            except Exception as err:
                self.logger.error(
                    f"Ошибка при создании релиза для сервиса {service_name}",
                    {
                        "service_name": service_name,
                        "release_version": release_version,
                        "error": str(err),
                    }
                )
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise err

    async def update_release(
            self,
            release_id: int,
            status: model.ReleaseStatus = None,
            github_run_id: str = None,
            github_action_link: str = None,
    ) -> None:
        with self.tracer.start_as_current_span(
                "ReleaseService.update_release",
                kind=SpanKind.INTERNAL,
                attributes={
                    "release_id": release_id,
                    "new_status": status.value,
                }
        ) as span:
            try:
                await self.release_repo.update_release(
                    release_id=release_id,
                    status=status,
                    github_run_id=github_run_id,
                    github_action_link=github_action_link,
                )

                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise err
from datetime import datetime
from aiogram_dialog import DialogManager
from opentelemetry.trace import SpanKind, Status, StatusCode

from internal import interface, model


class ActiveReleaseGetter(interface.IActiveReleaseGetter):
    def __init__(
            self,
            tel: interface.ITelemetry,
            release_repo: interface.IReleaseRepo
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.release_repo = release_repo

    async def get_releases_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        with self.tracer.start_as_current_span(
                "ActiveReleaseGetter.get_releases_data",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                # Получаем активные релизы
                releases = await self.release_repo.get_active_release()

                # Текущая страница
                current_page = dialog_manager.dialog_data.get("current_page", 0)

                data: dict = {
                    "has_releases": len(releases) > 0,
                    "total_pages": len(releases) if releases else 1,
                    "show_manual_testing_buttons": False,
                }

                if releases and current_page < len(releases):
                    current_release = releases[current_page]

                    # Форматируем данные релиза
                    release_data = {
                        "service_name": current_release.service_name,
                        "release_version": current_release.release_version,
                        "status_text": self._format_status(current_release.status),
                        "initiated_by": current_release.initiated_by,
                        "created_at_formatted": self._format_datetime(current_release.created_at),
                        "github_action_link": current_release.github_action_link,
                    }

                    data["current_release"] = release_data

                    # Показываем кнопки только для релизов в статусе manual_testing
                    if current_release.status == model.ReleaseStatus.MANUAL_TESTING:
                        data["show_manual_testing_buttons"] = True
                        dialog_manager.dialog_data["current_release_id"] = current_release.id
                        dialog_manager.dialog_data["current_release"] = release_data

                span.set_status(Status(StatusCode.OK))
                return data

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise err

    async def get_confirm_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        with self.tracer.start_as_current_span(
                "ActiveReleaseGetter.get_confirm_data",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                data = {
                    "release_to_confirm": dialog_manager.dialog_data.get("current_release", {})
                }

                span.set_status(Status(StatusCode.OK))
                return data

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise err

    async def get_reject_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        with self.tracer.start_as_current_span(
                "ActiveReleaseGetter.get_reject_data",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                data = {
                    "release_to_reject": dialog_manager.dialog_data.get("current_release", {})
                }

                span.set_status(Status(StatusCode.OK))
                return data

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise err

    def _format_status(self, status: model.ReleaseStatus) -> str:
        status_map = {
            model.ReleaseStatus.INITIATED: "🔵 Инициирован",
            model.ReleaseStatus.BUILDING: "🔨 Сборка",
            model.ReleaseStatus.MANUAL_TESTING: "🧪 Ручное тестирование",
            model.ReleaseStatus.MANUAL_TEST_PASSED: "✅ Тест пройден",
            model.ReleaseStatus.MANUAL_TEST_FAILED: "❌ Тест провален",
            model.ReleaseStatus.DEPLOYING: "🚀 Деплой",
            model.ReleaseStatus.DEPLOYED: "✅ Задеплоен",
            model.ReleaseStatus.FAILED: "❌ Ошибка",
            model.ReleaseStatus.ROLLBACK: "⏪ Откат",
            model.ReleaseStatus.CANCELLED: "🚫 Отменен",
        }
        return status_map.get(status, status.value)

    def _format_datetime(self, dt: datetime) -> str:
        if dt:
            return dt.strftime("%d.%m.%Y %H:%M")
        return "—"
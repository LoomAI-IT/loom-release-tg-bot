from datetime import datetime, timezone
from aiogram_dialog import DialogManager
from opentelemetry.trace import SpanKind, Status, StatusCode

from internal import interface, model


class SuccessfulReleasesGetter(interface.ISuccessfulReleasesGetter):
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
                "SuccessfulReleasesGetter.get_releases_data",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                # Получаем успешные релизы
                releases = await self.release_repo.get_successful_releases()

                if not releases:
                    return {
                        "has_releases": False,
                        "total_count": 0,
                    }

                # Сохраняем список для навигации
                releases_list = []
                for release in releases:
                    releases_list.append(release.to_dict())

                dialog_manager.dialog_data["releases_list"] = releases_list

                # Устанавливаем текущий индекс (0 если не был установлен)
                if "current_index" not in dialog_manager.dialog_data:
                    dialog_manager.dialog_data["current_index"] = 0

                current_index = dialog_manager.dialog_data["current_index"]

                # Корректируем индекс если он выходит за границы
                if current_index >= len(releases):
                    current_index = len(releases) - 1
                    dialog_manager.dialog_data["current_index"] = current_index

                current_release = releases[current_index]

                # Форматируем данные релиза
                release_data = {
                    "service_name": current_release.service_name,
                    "release_version": current_release.release_version,
                    "status_text": self._format_status(current_release.status),
                    "initiated_by": current_release.initiated_by,
                    "created_at_formatted": self._format_datetime(current_release.created_at),
                    "deployed_at_formatted": self._format_datetime(current_release.completed_at),
                    "github_action_link": current_release.github_action_link,
                }

                data = {
                    "has_releases": True,
                    "total_count": len(releases),
                    "current_index": current_index + 1,
                    "has_prev": current_index > 0,
                    "has_next": current_index < len(releases) - 1,
                    **release_data,
                }

                self.logger.info("Список успешных релизов загружен")

                span.set_status(Status(StatusCode.OK))
                return data

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise err

    def _format_status(self, status: model.ReleaseStatus) -> str:
        """Форматирует статус релиза с эмодзи"""
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
        return status_map.get(status, status.value if hasattr(status, 'value') else str(status))

    def _format_datetime(self, dt: datetime) -> str:
        """Форматирует дату и время"""
        if not dt:
            return "—"

        try:
            if isinstance(dt, str):
                dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))

            return dt.strftime("%d.%m.%Y %H:%M")
        except Exception:
            return str(dt)
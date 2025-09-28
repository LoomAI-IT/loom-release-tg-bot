from datetime import datetime
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

    async def get_rollback_versions_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        """Получает данные для окна выбора версии отката"""
        with self.tracer.start_as_current_span(
                "SuccessfulReleasesGetter.get_rollback_versions_data",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                # Получаем текущий релиз и доступные версии из dialog_data
                current_release = dialog_manager.dialog_data.get("rollback_current_release", {})
                available_versions = dialog_manager.dialog_data.get("available_rollback_versions", [])

                # Форматируем данные версий для отображения
                formatted_versions = []
                for version in available_versions:
                    formatted_version = {
                        "id": version.get("id"),
                        "release_version": version.get("release_version"),
                        "deployed_at_formatted": self._format_datetime(version.get("completed_at")),
                        "initiated_by": version.get("initiated_by"),
                    }
                    formatted_versions.append(formatted_version)

                data = {
                    "service_name": current_release.get("service_name", "Неизвестно"),
                    "current_version": current_release.get("release_version", "Неизвестно"),
                    "available_versions": formatted_versions,
                    "has_versions": len(formatted_versions) > 0,
                }

                self.logger.info(
                    f"Загружены версии для отката: {len(formatted_versions)} версий"
                )

                span.set_status(Status(StatusCode.OK))
                return data

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                self.logger.error(f"Ошибка при получении версий для отката: {str(err)}")
                raise err

    async def get_rollback_confirm_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        """Получает данные для окна подтверждения отката"""
        with self.tracer.start_as_current_span(
                "SuccessfulReleasesGetter.get_rollback_confirm_data",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                # Получаем данные из dialog_data
                current_release = dialog_manager.dialog_data.get("rollback_current_release", {})
                target_version = dialog_manager.dialog_data.get("rollback_target_version", {})

                data = {
                    "service_name": current_release.get("service_name", "Неизвестно"),
                    "current_version": current_release.get("release_version", "Неизвестно"),
                    "target_version": target_version.get("release_version", "Неизвестно"),
                    "target_deployed_at": self._format_datetime(
                        target_version.get("completed_at")
                    ),
                    "target_initiated_by": target_version.get("initiated_by", "Неизвестно"),
                }

                self.logger.info(
                    f"Подготовка подтверждения отката: "
                    f"{data['service_name']} с {data['current_version']} на {data['target_version']}"
                )

                span.set_status(Status(StatusCode.OK))
                return data

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                self.logger.error(f"Ошибка при получении данных для подтверждения отката: {str(err)}")
                raise err

    def _format_status(self, status: model.ReleaseStatus) -> str:
        """Форматирует статус релиза с эмодзи"""
        status_map = {
            model.ReleaseStatus.INITIATED: "🔵 Инициирован",
            model.ReleaseStatus.BUILDING: "🔨 Сборка",
            model.ReleaseStatus.STAGING_FAILED: "❌ Ошибка на stage",
            model.ReleaseStatus.MANUAL_TESTING: "🧪 Ручное тестирование",
            model.ReleaseStatus.MANUAL_TEST_PASSED: "✅ Тест пройден",
            model.ReleaseStatus.MANUAL_TEST_FAILED: "❌ Отклонен",
            model.ReleaseStatus.DEPLOYING: "🚀 Деплой",
            model.ReleaseStatus.DEPLOYED: "✅ Задеплоен",
            model.ReleaseStatus.PRODUCTION_FAILED: "❌ Ошибка на prod",
        }
        return status_map.get(status, status.value if hasattr(status, 'value') else str(status))

    def _format_datetime(self, dt: datetime) -> str:
        """Форматирует дату и время"""
        if not dt:
            return "—"

        try:
            # Обработка строкового представления datetime
            if isinstance(dt, str):
                # Пробуем разные форматы
                for fmt in [
                    "%Y-%m-%dT%H:%M:%S.%fZ",
                    "%Y-%m-%dT%H:%M:%SZ",
                    "%Y-%m-%dT%H:%M:%S.%f",
                    "%Y-%m-%dT%H:%M:%S",
                    "%Y-%m-%d %H:%M:%S.%f",
                    "%Y-%m-%d %H:%M:%S",
                ]:
                    try:
                        dt = datetime.strptime(dt, fmt)
                        break
                    except ValueError:
                        continue

                # Если не удалось распарсить, пробуем через fromisoformat
                if isinstance(dt, str):
                    dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))

            return dt.strftime("%d.%m.%Y %H:%M")
        except Exception as e:
            self.logger.warning(f"Ошибка форматирования даты: {e}, исходное значение: {dt}")
            return str(dt)
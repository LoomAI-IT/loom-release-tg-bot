from typing import Any

from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager, ShowMode
from opentelemetry.trace import SpanKind, Status, StatusCode

from internal import interface, model


class SuccessfulReleasesService(interface.ISuccessfulReleasesService):
    def __init__(
            self,
            tel: interface.ITelemetry,
            release_service: interface.IReleaseService,
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.release_service = release_service

    async def handle_navigate_release(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        """Обработка навигации между релизами"""
        with self.tracer.start_as_current_span(
                "SuccessfulReleasesService.handle_navigate_release",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                current_index = dialog_manager.dialog_data.get("current_index", 0)
                releases_list = dialog_manager.dialog_data.get("releases_list", [])

                # Определяем направление навигации
                if button.widget_id == "prev_release":
                    new_index = max(0, current_index - 1)
                else:  # next_release
                    new_index = min(len(releases_list) - 1, current_index + 1)

                if new_index == current_index:
                    await callback.answer()
                    return

                # Обновляем индекс
                dialog_manager.dialog_data["current_index"] = new_index

                self.logger.info("Навигация по успешным релизам")

                await callback.answer()
                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                await callback.answer("❌ Ошибка навигации", show_alert=True)
                raise err

    async def handle_refresh(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        """Обработка обновления списка релизов"""
        with self.tracer.start_as_current_span(
                "SuccessfulReleasesService.handle_refresh",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                dialog_manager.show_mode = ShowMode.EDIT

                # Сбрасываем индекс к первому релизу
                dialog_manager.dialog_data["current_index"] = 0

                # Очищаем кешированные данные
                dialog_manager.dialog_data.pop("releases_list", None)

                await callback.answer("✅ Данные обновлены")

                self.logger.info("Обновление списка успешных релизов")
                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                await callback.answer("❌ Ошибка при обновлении", show_alert=True)
                raise err

    async def handle_back_to_menu(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        """Обработка возврата в главное меню"""
        with self.tracer.start_as_current_span(
                "SuccessfulReleasesService.handle_back_to_menu",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                dialog_manager.show_mode = ShowMode.EDIT

                # Очищаем данные диалога
                dialog_manager.dialog_data.clear()

                await dialog_manager.start(model.MainMenuStates.main_menu)

                self.logger.info("Возврат в главное меню из успешных релизов")
                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                await callback.answer("❌ Ошибка", show_alert=True)
                raise err

    async def handle_rollback_click(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        """Обработка нажатия кнопки отката"""
        with self.tracer.start_as_current_span(
                "SuccessfulReleasesService.handle_rollback_click",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                dialog_manager.show_mode = ShowMode.EDIT

                # Получаем текущий релиз из списка
                current_index = dialog_manager.dialog_data.get("current_index", 0)
                releases_list = dialog_manager.dialog_data.get("releases_list", [])

                if not releases_list or current_index >= len(releases_list):
                    await callback.answer("❌ Ошибка получения данных релиза", show_alert=True)
                    return

                current_release = releases_list[current_index]

                # Сохраняем информацию о текущем релизе для отката
                dialog_manager.dialog_data["rollback_current_release"] = current_release

                # Получаем последние 3 успешных релиза для этого сервиса
                service_name = current_release.get("service_name")

                # Загружаем все успешные релизы для этого сервиса
                all_successful_releases = await self.release_service.get_successful_releases()

                # Фильтруем по сервису и берем последние 3 (исключая текущий)
                service_releases = [
                    r for r in all_successful_releases
                    if r.service_name == service_name and r.id != current_release.get("id")
                ][:3]

                if not service_releases:
                    await callback.answer(
                        "❌ Нет доступных версий для отката",
                        show_alert=True
                    )
                    return

                # Сохраняем доступные версии для отката
                dialog_manager.dialog_data["available_rollback_versions"] = [
                    r.to_dict() for r in service_releases
                ]

                # Переходим к выбору версии
                await dialog_manager.switch_to(model.SuccessfulReleasesStates.select_rollback_version)

                self.logger.info(f"Инициирован откат для сервиса {service_name}")
                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                await callback.answer("❌ Ошибка при инициализации отката", show_alert=True)
                raise err

    async def handle_version_selected(
            self,
            callback: CallbackQuery,
            widget: Any,
            dialog_manager: DialogManager,
            item_id: str
    ) -> None:
        """Обработка выбора версии для отката"""
        with self.tracer.start_as_current_span(
                "SuccessfulReleasesService.handle_version_selected",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                dialog_manager.show_mode = ShowMode.EDIT

                # Получаем доступные версии
                available_versions = dialog_manager.dialog_data.get("available_rollback_versions", [])

                # Находим выбранную версию
                selected_version = None
                for version in available_versions:
                    if str(version.get("id")) == item_id:
                        selected_version = version
                        break

                if not selected_version:
                    await callback.answer("❌ Версия не найдена", show_alert=True)
                    return

                # Сохраняем выбранную версию
                dialog_manager.dialog_data["rollback_target_version"] = selected_version

                # Переходим к подтверждению
                await dialog_manager.switch_to(model.SuccessfulReleasesStates.confirm_rollback)

                self.logger.info(
                    f"Выбрана версия для отката: {selected_version.get('release_version')}"
                )
                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                await callback.answer("❌ Ошибка при выборе версии", show_alert=True)
                raise err

    async def handle_confirm_rollback(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        """Обработка подтверждения отката"""
        with self.tracer.start_as_current_span(
                "SuccessfulReleasesService.handle_confirm_rollback",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                dialog_manager.show_mode = ShowMode.EDIT

                # Получаем данные для отката
                current_release = dialog_manager.dialog_data.get("rollback_current_release")
                target_version = dialog_manager.dialog_data.get("rollback_target_version")

                if not current_release or not target_version:
                    await callback.answer("❌ Ошибка получения данных для отката", show_alert=True)
                    return

                service_name = current_release.get("service_name")
                target_tag = target_version.get("release_version")

                self.logger.info(f"Начинаем откат сервиса {service_name} на версию {target_tag}")

                await self.release_service.update_release(
                    release_id=current_release.get("id"),
                    rollback_to_version=target_tag
                )

                await callback.answer(
                    f"✅ Откат на версию {target_tag} запущен!\n"
                    f"Процесс может занять несколько минут.",
                    show_alert=True
                )

                # Вызываем метод отката
                await self.release_service.rollback_to_tag(
                    service_name=service_name,
                    target_tag=target_tag
                )

                # Очищаем данные отката
                dialog_manager.dialog_data.pop("rollback_current_release", None)
                dialog_manager.dialog_data.pop("available_rollback_versions", None)
                dialog_manager.dialog_data.pop("rollback_target_version", None)

                # Возвращаемся к списку успешных релизов
                await dialog_manager.switch_to(model.SuccessfulReleasesStates.view_releases)

                self.logger.info(f"Откат сервиса {service_name} на версию {target_tag} успешно инициирован")
                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))

                await callback.answer("Ошибка", show_alert=True)
                raise err
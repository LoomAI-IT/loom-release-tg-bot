from aiogram_dialog import Window, Dialog
from aiogram_dialog.widgets.text import Const, Format, Case, Multi
from aiogram_dialog.widgets.kbd import Button, Column, Row
from sulguk import SULGUK_PARSE_MODE

from internal import interface, model


class SuccessfulReleasesDialog(interface.ISuccessfulReleasesDialog):
    def __init__(
            self,
            tel: interface.ITelemetry,
            successful_releases_service: interface.ISuccessfulReleasesService,
            successful_releases_getter: interface.ISuccessfulReleasesGetter,
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.successful_releases_service = successful_releases_service
        self.successful_releases_getter = successful_releases_getter

    def get_dialog(self) -> Dialog:
        return Dialog(
            self.get_view_successful_releases_window(),
        )

    def get_view_successful_releases_window(self) -> Window:
        return Window(
            Multi(
                Const("✅ <b>Успешные релизы</b><br><br>"),
                Case(
                    {
                        True: Multi(
                            Format("📦 <b>{service_name}</b><br>"),
                            Format("🏷️ <b>Версия:</b> <code>{release_version}</code><br>"),
                            Format("🔄 <b>Статус:</b> {status_text}<br>"),
                            Format("👤 <b>Инициатор:</b> <code>{initiated_by}</code><br>"),
                            Format("📅 <b>Создан:</b> <code>{created_at_formatted}</code><br>"),
                            Format("🚀 <b>Задеплоен:</b> <code>{deployed_at_formatted}</code><br>"),
                            Format("🔗 <b>GitHub Action:</b> <a href='{github_action_link}'>Открыть</a><br>"),
                        ),
                        False: Multi(
                            Const("📭 <b>Нет успешных релизов</b><br><br>"),
                            Const("💡 <i>Успешные релизы появятся здесь после завершения деплоя</i>"),
                        ),
                    },
                    selector="has_releases"
                ),
                sep="",
            ),

            # Навигация по релизам
            Row(
                Button(
                    Const("⬅️ Пред"),
                    id="prev_release",
                    on_click=self.successful_releases_service.handle_navigate_release,
                    when="has_prev",
                ),
                Button(
                    Format("📊 {current_index}/{total_count}"),
                    id="counter",
                    on_click=lambda c, b, d: c.answer("📈 Навигация по релизам"),
                    when="has_releases",
                ),
                Button(
                    Const("➡️ След"),
                    id="next_release",
                    on_click=self.successful_releases_service.handle_navigate_release,
                    when="has_next",
                ),
                when="has_releases",
            ),

            Column(
                Button(
                    Const("🔄 Обновить"),
                    id="refresh",
                    on_click=self.successful_releases_service.handle_refresh,
                    when="has_releases",
                ),
                Button(
                    Const("⬅️ Назад в меню"),
                    id="back_to_menu",
                    on_click=self.successful_releases_service.handle_back_to_menu,
                ),
            ),

            state=model.SuccessfulReleasesStates.view_releases,
            getter=self.successful_releases_getter.get_releases_data,
            parse_mode=SULGUK_PARSE_MODE,
        )
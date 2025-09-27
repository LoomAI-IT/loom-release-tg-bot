from aiogram import F
from aiogram_dialog import Window, Dialog
from aiogram_dialog.widgets.text import Const, Format, Case, Multi
from aiogram_dialog.widgets.kbd import Button, Column, Row, Group, Back, Cancel
from aiogram_dialog.widgets.kbd import NumberedPager, StubScroll
from sulguk import SULGUK_PARSE_MODE

from internal import interface, model


class ActiveReleaseDialog(interface.IActiveReleaseDialog):
    def __init__(
            self,
            tel: interface.ITelemetry,
            active_release_service: interface.IActiveReleaseService,
            active_release_getter: interface.IActiveReleaseGetter,
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.active_release_service = active_release_service
        self.active_release_getter = active_release_getter

    def get_dialog(self) -> Dialog:
        return Dialog(
            self.get_view_releases_window(),
            self.get_confirm_dialog_window(),
            self.get_reject_dialog_window(),
        )

    def get_view_releases_window(self) -> Window:
        return Window(
            Const("<b>🚀 Активные релизы</b>\n"),
            Case(
                {
                    True: Multi(
                        Const("━━━━━━━━━━━━━━━━━━━━━\n"),
                        Format("<b>Сервис:</b> {current_release[service_name]}\n"),
                        Format("<b>Версия:</b> {current_release[release_version]}\n"),
                        Format("<b>Статус:</b> {current_release[status_text]}\n"),
                        Format("<b>Инициатор:</b> {current_release[initiated_by]}\n"),
                        Format("<b>Создан:</b> {current_release[created_at_formatted]}\n"),
                        Case(
                            {
                                True: Format("<b>GitHub Action:</b> <a href='{current_release[github_action_link]}'>Открыть</a>\n"),
                                False: Const(""),
                            },
                            selector=F["current_release"]["github_action_link"]
                        ),
                        Const("━━━━━━━━━━━━━━━━━━━━━"),
                    ),
                    False: Const("📭 Нет активных релизов"),
                },
                selector="has_releases"
            ),
            # Навигация по релизам
            Group(
                NumberedPager(
                    scroll="release_scroll",
                    when="has_releases"
                ),
                width=5,
            ),
            StubScroll(
                id="release_scroll",
                pages="total_pages"
            ),
            Column(
                Row(
                    Button(
                        Const("✅ Подтвердить"),
                        id="confirm_release",
                        on_click=self.active_release_service.handle_confirm_release,
                        when=F["show_manual_testing_buttons"]
                    ),
                    Button(
                        Const("❌ Отклонить"),
                        id="reject_release",
                        on_click=self.active_release_service.handle_reject_release,
                        when=F["show_manual_testing_buttons"]
                    ),
                ),
                Button(
                    Const("🔄 Обновить"),
                    id="refresh",
                    on_click=self.active_release_service.handle_refresh,
                ),
                Cancel(
                    Const("⬅️ Назад в меню"),
                ),
            ),
            state=model.ActiveReleaseStates.view_releases,
            getter=self.active_release_getter.get_releases_data,
            parse_mode=SULGUK_PARSE_MODE,
        )

    def get_confirm_dialog_window(self) -> Window:
        return Window(
            Const("<b>✅ Подтверждение релиза</b>\n\n"),
            Format("Вы уверены, что хотите подтвердить релиз?\n\n"),
            Format("<b>Сервис:</b> {release_to_confirm[service_name]}\n"),
            Format("<b>Версия:</b> {release_to_confirm[release_version]}\n"),
            Row(
                Button(
                    Const("✅ Да, подтвердить"),
                    id="confirm_yes",
                    on_click=self.active_release_service.handle_confirm_yes,
                ),
                Back(
                    Const("❌ Отмена"),
                ),
            ),
            state=model.ActiveReleaseStates.confirm_dialog,
            getter=self.active_release_getter.get_confirm_data,
            parse_mode=SULGUK_PARSE_MODE,
        )

    def get_reject_dialog_window(self) -> Window:
        return Window(
            Const("<b>❌ Отклонение релиза</b>\n\n"),
            Format("Вы уверены, что хотите отклонить релиз?\n\n"),
            Format("<b>Сервис:</b> {release_to_reject[service_name]}\n"),
            Format("<b>Версия:</b> {release_to_reject[release_version]}\n"),
            Row(
                Button(
                    Const("❌ Да, отклонить"),
                    id="reject_yes",
                    on_click=self.active_release_service.handle_reject_yes,
                ),
                Back(
                    Const("✅ Отмена"),
                ),
            ),
            state=model.ActiveReleaseStates.reject_dialog,
            getter=self.active_release_getter.get_reject_data,
            parse_mode=SULGUK_PARSE_MODE,
        )
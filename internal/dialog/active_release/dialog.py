from aiogram_dialog import Window, Dialog
from aiogram_dialog.widgets.text import Const, Format, Case, Multi
from aiogram_dialog.widgets.kbd import Button, Column, Row
from sulguk import SULGUK_PARSE_MODE

from internal import interface, model


class ActiveReleaseDialog(interface.IActiveReleaseDialog):
    def __init__(
            self,
            tel: interface.ITelemetry,
            active_release_service: interface.IActiveReleaseService,
            active_release_getter: interface.IActiveReleaseGetter,
            required_approvers: list[str] = None,  # Новый параметр для списка обязательных подтверждающих
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.active_release_service = active_release_service
        self.active_release_getter = active_release_getter
        self.required_approvers = required_approvers or ["@user1", "@user2"]

    def get_dialog(self) -> Dialog:
        return Dialog(
            self.get_view_releases_window(),
            self.get_confirm_dialog_window(),
            self.get_reject_dialog_window(),
        )

    def get_view_releases_window(self) -> Window:
        return Window(
            Multi(
                Const("🚀 <b>Активные релизы</b><br><br>"),
                Case(
                    {
                        True: Multi(
                            Format("📦 <b>{service_name}</b><br>"),
                            Case(
                                {
                                    False: Format("🏷️ <b>Tag:</b> <code>{current_tag}</code><br>"),
                                    True: Multi(
                                        Format("🏷️ <b>Текущий tag:</b> <code>{current_tag}</code><br>"),
                                        Format("🏷️ <b>Прошлый tag:</b> <code>{old_tag}</code><br>"),
                                    ),
                                },
                                selector="has_rollback"
                            ),
                            Format("🔄 <b>Статус:</b> {status_text}<br>"),
                            Format("👤 <b>Инициатор:</b> <code>{initiated_by}</code><br>"),
                            Format("📅 <b>Создан:</b> <code>{created_at_formatted}</code><br>"),
                            # Новый блок для отображения статуса подтверждений
                            Case(
                                {
                                    True: Multi(
                                        Const("✅ <b>Подтверждения:</b><br>"),
                                        Format("{approval_status}<br>"),
                                        Format("📋 <b>Прогресс:</b> {approval_progress}<br>"),
                                    ),
                                    False: Const(""),
                                },
                                selector="show_approval_status"
                            ),
                            Case(
                                {
                                    True: Format("🔗 <b>GitHub Action:</b> <a href='{github_action_link}'>Открыть</a><br>"),
                                    False: Const(""),
                                },
                                selector="has_github_link"
                            ),
                            Case(
                                {
                                    True: Format("⏱️ <b>В обработке:</b> <i>{waiting_time}</i><br>"),
                                    False: Const(""),
                                },
                                selector="has_waiting_time"
                            ),
                        ),
                        False: Multi(
                            Const("📭 <b>Нет активных релизов</b><br><br>"),
                            Const("💡 <i>Все релизы завершены или ещё не инициированы</i>"),
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
                    on_click=self.active_release_service.handle_navigate_release,
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
                    on_click=self.active_release_service.handle_navigate_release,
                    when="has_next",
                ),
                when="has_releases",
            ),

            Column(
                Row(
                    Button(
                        Const("✅ Подтвердить"),
                        id="confirm_release",
                        on_click=lambda c, b, d: d.switch_to(model.ActiveReleaseStates.confirm_dialog),
                        when="show_manual_testing_buttons"
                    ),
                    Button(
                        Const("❌ Отклонить"),
                        id="reject_release",
                        on_click=lambda c, b, d: d.switch_to(model.ActiveReleaseStates.reject_dialog),
                        when="show_manual_testing_buttons"
                    ),
                ),
                Button(
                    Const("🔄 Обновить"),
                    id="refresh",
                    on_click=self.active_release_service.handle_refresh,
                    when="has_releases",
                ),
                Button(
                    Const("⬅️ Назад в меню"),
                    id="back_to_menu",
                    on_click=self.active_release_service.handle_back_to_menu,
                ),
            ),

            state=model.ActiveReleaseStates.view_releases,
            getter=self.active_release_getter.get_releases_data,
            parse_mode=SULGUK_PARSE_MODE,
        )

    def get_confirm_dialog_window(self) -> Window:
        return Window(
            Multi(
                Const("✅ <b>Подтверждение релиза</b><br><br>"),
                Format("Вы уверены, что хотите подтвердить релиз?<br><br>"),
                Format("📦 <b>Сервис:</b> <code>{service_name}</code><br>"),
                Format("🏷️ <b>Tag:</b> <code>{release_tag}</code><br>"),
                Format("👤 <b>Инициатор:</b> <code>{initiated_by}</code><br>"),
                # Отображение текущего статуса подтверждений
                Format("✅ <b>Текущие подтверждения:</b><br>{approval_status}<br>"),
                Format("📋 <b>Прогресс:</b> {approval_progress}<br><br>"),
                Case(
                    {
                        True: Const("⚠️ <i>Ваше подтверждение будет добавлено к релизу</i>"),
                        False: Const("⚠️ <i>После получения всех подтверждений релиз будет автоматически продолжен</i>"),
                    },
                    selector="user_already_approved"
                ),
                sep="",
            ),
            Row(
                Button(
                    Const("✅ Да, подтвердить"),
                    id="confirm_yes",
                    on_click=self.active_release_service.handle_confirm_yes
                ),
                Button(
                    Const("❌ Отмена"),
                    id="cancel_confirm",
                    on_click=lambda c, b, d: d.switch_to(model.ActiveReleaseStates.view_releases),
                ),
            ),
            state=model.ActiveReleaseStates.confirm_dialog,
            getter=self.active_release_getter.get_confirm_data,
            parse_mode=SULGUK_PARSE_MODE,
        )

    def get_reject_dialog_window(self) -> Window:
        return Window(
            Multi(
                Const("❌ <b>Отклонение релиза</b><br><br>"),
                Format("Вы уверены, что хотите отклонить релиз?<br><br>"),
                Format("📦 <b>Сервис:</b> <code>{service_name}</code><br>"),
                Format("🏷️ <b>Tag:</b> <code>{release_tag}</code><br>"),
                Format("👤 <b>Инициатор:</b> <code>{initiated_by}</code><br><br>"),
                Const("⚠️ <i>После отклонения релиз будет отмечен как неуспешный</i>"),
                sep="",
            ),
            Row(
                Button(
                    Const("❌ Да, отклонить"),
                    id="reject_yes",
                    on_click=self.active_release_service.handle_reject_yes,
                ),
                Button(
                    Const("✅ Отмена"),
                    id="cancel_reject",
                    on_click=lambda c, b, d: d.switch_to(model.ActiveReleaseStates.view_releases),
                ),
            ),
            state=model.ActiveReleaseStates.reject_dialog,
            getter=self.active_release_getter.get_reject_data,
            parse_mode=SULGUK_PARSE_MODE,
        )
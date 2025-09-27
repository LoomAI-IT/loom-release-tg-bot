import traceback

from aiogram.types import Message
from aiogram_dialog import DialogManager, StartMode
from opentelemetry.trace import SpanKind, StatusCode

from internal import model, interface


class CommandController(interface.ICommandController):

    def __init__(
            self,
            tel: interface.ITelemetry,
            state_service: interface.IStateService
    ):
        self.logger = tel.logger()
        self.tracer = tel.tracer()
        self.state_service = state_service

    async def start_handler(
            self,
            message: Message,
            dialog_manager: DialogManager
    ):
        with (self.tracer.start_as_current_span(
                "CommandController.start_handler",
                kind=SpanKind.INTERNAL
        ) as span):
            try:
                await dialog_manager.reset_stack()

                tg_chat_id = dialog_manager.event.chat.id

                user_state = await self.state_service.state_by_id(tg_chat_id)
                if not user_state:
                    tg_username = message.from_user.username if message.from_user.username else "отсутвует username"
                    await self.state_service.create_state(tg_chat_id, tg_username)

                span.set_status(StatusCode.OK)
            except Exception as err:
                span.record_exception(err)
                span.set_status(StatusCode.ERROR, str(err))
                raise err
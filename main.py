import uvicorn
from aiogram import Bot, Dispatcher
import redis.asyncio as redis
from aiogram.fsm.storage.base import DefaultKeyBuilder
from aiogram.fsm.storage.redis import RedisStorage
from sulguk import AiogramSulgukMiddleware

from infrastructure.pg.pg import PG
from infrastructure.telemetry.telemetry import Telemetry, AlertManager


from internal.controller.http.middlerware.middleware import HttpMiddleware
from internal.controller.tg.middleware.middleware import TgMiddleware

from internal.controller.tg.command.handler import CommandController
from internal.controller.http.webhook.handler import TelegramWebhookController

from internal.dialog.main_menu.dialog import MainMenuDialog

from internal.service.state.service import StateService
from internal.dialog.main_menu.service import MainMenuService

from internal.dialog.main_menu.getter import MainMenuGetter

from internal.repo.state.repo import StateRepo

from internal.app.tg.app import NewTg
from internal.app.server.app import NewServer

from internal.config.config import Config

cfg = Config()

# Инициализация мониторинга
alert_manager = AlertManager(
    cfg.alert_tg_bot_token,
    cfg.service_name,
    cfg.alert_tg_chat_id,
    cfg.alert_tg_chat_thread_id,
    cfg.grafana_url,
    cfg.monitoring_redis_host,
    cfg.monitoring_redis_port,
    cfg.monitoring_redis_db,
    cfg.monitoring_redis_password
)

tel = Telemetry(
    cfg.log_level,
    cfg.root_path,
    cfg.environment,
    cfg.service_name,
    cfg.service_version,
    cfg.otlp_host,
    cfg.otlp_port,
    alert_manager
)

redis_client = redis.Redis(
    host=cfg.monitoring_redis_host,
    port=cfg.monitoring_redis_port,
    password=cfg.monitoring_redis_password,
    db=2
)
key_builder = DefaultKeyBuilder(with_destiny=True)
storage = RedisStorage(
    redis=redis_client,
    key_builder=key_builder
)
dp = Dispatcher(storage=storage)
bot = Bot(token=cfg.tg_bot_token)
bot.session.middleware(AiogramSulgukMiddleware())

# Инициализация клиентов
db = PG(tel, cfg.db_user, cfg.db_pass, cfg.db_host, cfg.db_port, cfg.db_name)

state_repo = StateRepo(tel, db)


main_menu_getter = MainMenuGetter(
    tel,
    state_repo
)

# Инициализация сервисов
state_service = StateService(tel, state_repo)
main_menu_service = MainMenuService(
    tel,
    bot,
    state_repo,
)

main_menu_dialog = MainMenuDialog(
    tel,
    main_menu_service,
    main_menu_getter
)


command_controller = CommandController(tel, state_service)

dialog_bg_factory = NewTg(
    dp,
    command_controller,
    main_menu_dialog,
)

# Инициализация middleware
tg_middleware = TgMiddleware(
    tel,
    state_service,
    bot,
    dialog_bg_factory
)
http_middleware = HttpMiddleware(
    tel,
    cfg.prefix,
)
tg_webhook_controller = TelegramWebhookController(
    tel,
    dp,
    bot,
    state_service,
    dialog_bg_factory,
    cfg.domain,
    cfg.prefix,
    cfg.interserver_secret_key
)

if __name__ == "__main__":
    app = NewServer(
        db,
        http_middleware,
        tg_webhook_controller,
        cfg.prefix,
    )
    uvicorn.run(app, host="0.0.0.0", port=int(cfg.http_port), access_log=False)

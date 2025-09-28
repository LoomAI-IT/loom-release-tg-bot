import io
import time

import asyncssh
from opentelemetry.trace import SpanKind, Status, StatusCode

from internal import interface, model


class ReleaseService(interface.IReleaseService):
    def __init__(
            self,
            tel: interface.ITelemetry,
            release_repo: interface.IReleaseRepo,
            prod_host: str,
            prod_password: str,
            service_port_map: dict[str, int]
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.release_repo = release_repo
        self.prod_host = prod_host
        self.prod_password = prod_password
        self.service_port_map = service_port_map

    async def create_release(
            self,
            service_name: str,
            release_tag: str,
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
                    "release_tag": release_tag,
                    "initiated_by": initiated_by,
                    "github_run_id": github_run_id,
                    "github_ref": github_ref,
                }
        ) as span:
            try:
                release_id = await self.release_repo.create_release(
                    service_name=service_name,
                    release_tag=release_tag,
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
                        "release_tag": release_tag,
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
            rollback_to_tag: str = None,
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
                    rollback_to_tag=rollback_to_tag,
                )

                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise err

    async def get_active_release(self) -> list[model.Release]:
        with self.tracer.start_as_current_span(
                "ReleaseService.get_active_release",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                releases = await self.release_repo.get_active_release()

                span.set_status(Status(StatusCode.OK))
                return releases

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise err

    async def get_successful_releases(self) -> list[model.Release]:
        with self.tracer.start_as_current_span(
                "ReleaseService.get_successful_releases",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                releases = await self.release_repo.get_successful_releases( )

                span.set_status(Status(StatusCode.OK))
                return releases

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise err

    async def get_failed_releases(self) -> list[model.Release]:
        with self.tracer.start_as_current_span(
                "ReleaseService.get_failed_releases",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                releases = await self.release_repo.get_failed_releases()

                span.set_status(Status(StatusCode.OK))
                return releases

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise err

    async def rollback_to_tag(
            self,
            service_name: str,
            target_tag: str,
    ):
        async with asyncssh.connect(
                host=self.prod_host,
                username="root",
                password=self.prod_password,
                connect_timeout=30,
                known_hosts=None
        ) as conn:
            timestamp = int(time.time())
            script_file = f"/tmp/rollback_{service_name}_{target_tag}_{timestamp}.sh"

            rollback_script = self._generate_rollback_command(
                service_name=service_name,
                target_tag=target_tag,
            )

            # Upload the script to the server
            async with conn.start_sftp_client() as sftp:
                async with sftp.open(script_file, 'w') as remote_file:
                    await remote_file.write(rollback_script)

            # Делаем скрипт исполняемым и запускаем в фоне
            command = f"chmod +x {script_file} && nohup bash {script_file} > /dev/null 2>&1 & echo $!"

            await conn.run(command, check=False)

    def _generate_rollback_command(self, service_name: str, target_tag: str) -> str:
        prefix = f"/api/{service_name.replace("loom-", "")}"
        port = self.service_port_map[service_name]

        rollback_commands = f"""# Откат сервиса {service_name} на версию {target_tag}
set -e

# Создаем директорию для логов если её нет
mkdir -p /var/log/deployments/rollback/{service_name}

# Создаем файл лога с именем версии для отката
LOG_FILE="/var/log/deployments/rollback/{service_name}/{target_tag}-rollback.log"

# Функция для логирования
log_message() {{
    local message="$1"
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $message" | tee -a "$LOG_FILE"
}}

log_message "🔄 Начинаем откат сервиса {service_name} на версию {target_tag}"

# 1. Переходим в директорию сервиса
cd loom/{service_name}

# 2. Сохраняем текущее состояние для проверки
CURRENT_REF=$(git symbolic-ref --short HEAD 2>/dev/null || git describe --tags --exact-match 2>/dev/null || git rev-parse --short HEAD)
log_message "🔍 Текущее состояние до отката: $CURRENT_REF"

# 3. Обновляем репозиторий и версии
log_message "📥 Обновляем репозиторий и теги для отката..."

if git tag -l | grep -q "^{target_tag}$"; then
    log_message "🏷️ Локальный тег {target_tag} уже существует, удаляем для обновления"
    git tag -d {target_tag} 2>&1 | tee -a "$LOG_FILE"
fi

log_message "📥 Получаем обновления из удаленного репозитория"
git fetch origin 2>&1 | tee -a "$LOG_FILE"

log_message "📥 Принудительно обновляем теги"
git fetch origin --tags --force 2>&1 | tee -a "$LOG_FILE"

# 4. Проверяем наличие целевого тега
if ! git tag -l | grep -q "^{target_tag}$"; then
    log_message "❌ Тег {target_tag} не найден в репозитории после обновления!"
    log_message "📋 Доступные теги:"
    git tag -l | tail -10 | tee -a "$LOG_FILE"
    exit 1
fi

log_message "✅ Тег {target_tag} найден и готов к использованию для отката"

# 5. Переключаемся на целевой тег
log_message "🔄 Переключаемся на тег {target_tag} для отката..."
git checkout {target_tag} 2>&1 | tee -a "$LOG_FILE"

# Очищаем старые ветки (кроме main/master)
log_message "🧹 Очищаем старые ветки"
git for-each-ref --format='%(refname:short)' refs/heads | grep -v -E "^(main|master)$" | xargs -r git branch -D 2>&1 | tee -a "$LOG_FILE"

# Очищаем удаленные ветки
log_message "🧹 Очищаем удаленные ветки"
git remote prune origin 2>&1 | tee -a "$LOG_FILE"

log_message "✅ Переключение на тег {target_tag} для отката завершено"

# 6. Переходим в директорию системы
cd ../loom-system

# 7. Загружаем переменные окружения
export $(cat env/.env.app env/.env.db env/.env.monitoring | xargs)

log_message "🔨 Начинаем пересборку контейнера для отката на тег {target_tag}..."

log_message "🔧 Запускаем контейнер с откаченной версией..."
docker compose -f ./docker-compose/app.yaml up -d --build {service_name} 2>&1 | tee -a "$LOG_FILE"

# Показываем информацию о созданных образах
log_message "📋 Созданные образы после отката:"
docker images | grep {service_name} | tee -a "$LOG_FILE"

# 8. Проверяем здоровье сервиса после отката
check_health() {{
    # Если есть HTTP endpoint
    if curl -f -s -o /dev/null -w "%{{http_code}}" http://localhost:{port}/{prefix}/health | grep -q "200"; then
        return 0
    else
        return 1
    fi
}}

MAX_ATTEMPTS=5
ATTEMPT=1
SUCCESS=false

log_message "⏳ Ждем запуска сервиса после отката..."
sleep 15

while [ $ATTEMPT -le $MAX_ATTEMPTS ]; do
    log_message "🔍 Проверка health после отката (попытка $ATTEMPT из $MAX_ATTEMPTS)..."

    if check_health; then
        log_message "✅ Health check пройден после отката!"
        SUCCESS=true
        break
    else
        log_message "⏳ Health check не пройден, ждем..."
        sleep 20
    fi

    ATTEMPT=$((ATTEMPT + 1))
done

if [ "$SUCCESS" = false ]; then
    log_message "❌ Health check не пройден после $MAX_ATTEMPTS попыток"
    log_message "📋 Логи контейнера:"
    docker logs --tail 100 {service_name} 2>&1 | tee -a "$LOG_FILE"
    exit 1
fi

log_message "🎉 Откат на тег {target_tag} завершен успешно! Сервис работает!"
log_message "📊 Сервис: {service_name}"
log_message "🏷️ Версия: {target_tag}"
log_message "✅ Статус: Успешно откачен"
log_message "📁 Лог отката сохранен в: $LOG_FILE"

# Выводим последние строки лога
echo "📋 Последние строки лога отката:"
tail -20 "$LOG_FILE" 
"""

        return rollback_commands

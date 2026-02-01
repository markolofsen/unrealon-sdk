# Unrealon SDK

Python SDK для мониторинга и управления сервисами через Unrealon платформу.

## Что даёт SDK

- **Мониторинг** — видишь статус сервиса в реальном времени
- **Логи в облако** — все логи доступны в веб-интерфейсе
- **Управление** — pause/resume/stop прямо из дашборда
- **Метрики** — счётчики обработанных элементов и ошибок

## Установка

```bash
pip install unrealon
```

## Быстрый старт

### Минимальный пример

```python
from unrealon import ServiceClient

with ServiceClient(api_key="pk_xxx", service_name="my-service") as client:
    client.info("Started")

    for item in items:
        process(item)
        client.increment_processed()

    client.info("Done")
```

Всё. Сервис зарегистрируется, логи пойдут в облако, метрики будут отображаться.

### С поддержкой pause/resume

```python
from unrealon import ServiceClient

with ServiceClient(api_key="pk_xxx", service_name="my-parser") as client:
    client.info("Started")

    for item in items:
        client.check_interrupt()  # Тут парсер встанет на паузу если нажать Pause

        process(item)
        client.increment_processed()

    client.info("Done")
```

`check_interrupt()` делает две вещи:
- Если нажали **Pause** — ждёт пока нажмут Resume
- Если нажали **Stop** — выбрасывает `StopInterrupt`

## Continuous Mode

Сервис который ждёт команд из дашборда:

```python
import time
from unrealon import ServiceClient
from unrealon.exceptions import StopInterrupt

with ServiceClient(api_key="pk_xxx", service_name="my-parser") as client:

    def handle_run(params: dict) -> dict:
        limit = params.get("limit", 100)

        client.set_busy()
        try:
            for i in range(limit):
                client.check_interrupt()
                do_work()
                client.increment_processed()
            return {"status": "ok"}
        except StopInterrupt:
            return {"status": "stopped"}
        finally:
            client.set_idle()

    client.on_command("run", handle_run)

    # Ждём команд
    client.set_idle()
    while not client.should_stop:
        time.sleep(1)
```

Теперь можно из дашборда:
- Нажать **Run** — запустится `handle_run`
- Нажать **Pause** — парсер встанет на `check_interrupt()`
- Нажать **Resume** — продолжит с того же места
- Нажать **Stop** — завершится gracefully

## API

### Логирование

```python
client.debug("Debug message")
client.info("Info message", key="value")
client.warning("Warning")
client.error("Error", code=500)
```

Логи идут в три места: консоль (Rich), файл, облако.

### Метрики

```python
client.increment_processed()      # +1 обработано
client.increment_processed(10)    # +10 обработано
client.increment_errors()         # +1 ошибка
```

### Статусы

```python
client.set_busy()    # Показывает "Busy" в дашборде
client.set_idle()    # Показывает "Idle"
```

### Состояние

```python
client.is_paused     # True если на паузе
client.should_stop   # True если запрошена остановка
client.is_connected  # True если подключен к серверу
```

### Команды

```python
# Регистрация обработчика
client.on_command("run", handle_run)
client.on_command("custom", handle_custom)

# Обработчик получает params и возвращает результат
def handle_run(params: dict) -> dict:
    limit = params.get("limit", 10)
    # ... do work ...
    return {"status": "ok", "processed": 100}
```

## Конфигурация

### Через переменные окружения

```bash
export UNREALON_API_KEY=pk_xxx
export UNREALON_SERVICE_NAME=my-service
```

```python
# Подхватит из env
with ServiceClient() as client:
    ...
```

### Dev mode (локальный сервер)

```python
with ServiceClient(
    api_key="dk_xxx",
    service_name="my-service",
    dev_mode=True,  # Подключится к localhost:50051
) as client:
    ...
```

## Exceptions

```python
from unrealon.exceptions import (
    StopInterrupt,        # Stop requested (наследует BaseException!)
    UnrealonError,        # Base SDK error
    AuthenticationError,  # Bad API key
    RegistrationError,    # Can't register
)

try:
    with ServiceClient(...) as client:
        for item in items:
            client.check_interrupt()
            process(item)
except StopInterrupt:
    print("Stopped by command")
```

**Важно**: `StopInterrupt` наследует `BaseException`, не `Exception`.
Это значит что `except Exception` его НЕ поймает — специально, чтобы
generic error handlers не глотали команду stop.

## Standalone Logger

Можно использовать логгер отдельно от SDK:

```python
from unrealon.logging import get_logger

log = get_logger("myapp")
log.info("Starting", version="1.0")
log.error("Failed", error="connection timeout")
```

Логи пойдут в консоль и файл (без облака).

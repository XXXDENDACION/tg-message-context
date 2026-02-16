# Telegram Context Bot

Бот для Telegram, который отслеживает реакции 👍 в чате и автоматически извлекает релевантный контекст обсуждения с помощью AI.

## Возможности

- Сохранение всех сообщений из отслеживаемого чата в локальную базу данных
- Отслеживание реакций 👍 на сообщения
- Извлечение контекста (10-20 сообщений) с учётом цепочек ответов
- AI-фильтрация релевантных сообщений (DeepSeek через OpenRouter)
- Публикация отфильтрованного контекста в целевой канал

## Технологии

- **Python 3.12**
- **aiogram 3.x** — Telegram Bot API
- **SQLAlchemy 2.0** — async ORM
- **SQLite** — хранение сообщений
- **OpenRouter API** — доступ к DeepSeek и другим моделям
- **Docker** — деплой

## Требования

- Docker и Docker Compose
- Telegram Bot Token (от [@BotFather](https://t.me/BotFather))
- OpenRouter API Key

## Установка

### 1. Клонировать репозиторий

```bash
git clone https://github.com/XXXDENDACION/tg-message-context.git
cd tg-message-context
```

### 2. Создать файл конфигурации

```bash
cp .env.example .env
```

### 3. Заполнить `.env`

```env
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_bot_token_here

# Chat IDs
SOURCE_CHAT_ID=-1001234567890
TARGET_CHANNEL_ID=-1001234567891

# OpenRouter Configuration
OPENROUTER_API_KEY=your-openrouter-api-key

# Context Settings
CONTEXT_MESSAGES_COUNT=20
```

#### Как получить значения:

| Переменная | Как получить |
|------------|--------------|
| `TELEGRAM_BOT_TOKEN` | Создать бота через [@BotFather](https://t.me/BotFather) |
| `SOURCE_CHAT_ID` | Переслать сообщение из чата в [@userinfobot](https://t.me/userinfobot) |
| `TARGET_CHANNEL_ID` | Переслать сообщение из канала в [@userinfobot](https://t.me/userinfobot) |
| `OPENROUTER_API_KEY` | [openrouter.ai/keys](https://openrouter.ai/keys) |

### 4. Настроить права бота

1. **В source-чате:**
   - Добавить бота в чат
   - Сделать администратором (нужно для чтения сообщений и реакций)
   - В @BotFather: `/setprivacy` → Disable (чтобы бот видел все сообщения)

2. **В target-канале:**
   - Добавить бота в канал
   - Дать права на публикацию сообщений

### 5. Запустить

```bash
docker-compose up --build
```

Для запуска в фоне:

```bash
docker-compose up -d --build
```

## Локальная разработка (без Docker)

```bash
# Создать виртуальное окружение
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# или
.venv\Scripts\activate  # Windows

# Установить зависимости
pip install -e .

# Запустить
python -m src.main
```

## Структура проекта

```
├── src/
│   ├── main.py              # Entry point
│   ├── config.py            # Pydantic settings
│   ├── bot/
│   │   └── handlers.py      # Message & reaction handlers
│   ├── db/
│   │   ├── database.py      # SQLAlchemy setup
│   │   ├── models.py        # Message model
│   │   └── repository.py    # CRUD operations
│   ├── ai/
│   │   └── openrouter_client.py # OpenRouter/DeepSeek integration
│   └── services/
│       └── context_service.py # Business logic
├── tests/
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
└── .env.example
```

## Как это работает

```
1. Бот сохраняет все сообщения из source-чата в SQLite

2. При реакции 👍 на сообщение:
   └── Если сообщение — ответ на старое → переход к началу треда
   └── Загрузка 20 сообщений начиная с этой точки

3. DeepSeek (через OpenRouter) анализирует сообщения:
   └── Фильтрует только релевантные к теме
   └── Исключает параллельные обсуждения

4. Отфильтрованные сообщения публикуются в target-канал
```

## Почему OpenRouter + DeepSeek?

- **Единый API** — доступ к множеству моделей через один интерфейс
- **DeepSeek** — отличное качество при низкой цене
- **Гибкость** — легко переключиться на другую модель

## Лицензия

MIT

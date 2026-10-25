# TeamGrief Ticket Bot (Python / discord.py 2.x)

Современный, быстрый и функциональный тикет-бот для Discord-сообщества **TeamGrief**, разработанный на Python с использованием интерактивных компонентов: постоянных кнопок (**Persistent Views**), модальных окон (**Modals**), выпадающих списков (**Select Menus**) и автогенерации HTML-транскриптов.

---

## 🌟 Возможности TeamGrief Bot

- 📩 **Стильная панель обращения**: отправляется с помощью `/ticket-panel`.
- 📋 **Категории обращений**:
  - 🛠️ **Техническая помощь / Краши** (баги, ошибки клиента, вылеты)
  - 💳 **Покупка / Ключи / Подписка** (активация, продление)
  - 🎬 **Заявка на Медиа** (YouTube, Twitch, TikTok, сотрудничество)
  - ⚠️ **Жалоба / Другое**
- 📝 **Модальные формы (Modals)**: пользователи заполняют тему и подробности прямо в Discord.
- 🔒 **Приватность**: доступ к тикет-каналу имеет только автор тикета и роль техподдержки/модерации TeamGrief.
- ⚡ **Постоянные кнопки (Persistent Views)**: кнопки и меню не «ломаются» после перезапуска бота.
- 📜 **HTML-транскрипты**: при закрытии тикета создаётся красивый автономный HTML-файл переписки в тёмном стиле Discord с аватарами и вложениями.
- 🗃️ **Архивация**: закрытый тикет отправляется в категорию `🔒・CLOSED TICKETS・📁` и скрывается от автора, с возможностью открыть заново или удалить навсегда.
- 👥 **Управление участниками**: добавление и исключение пользователей кнопками или командами `/ticket-add`, `/ticket-remove`.

---

## 🚀 Настройка и запуск

### 1. Создание бота в Discord Developer Portal
1. Откройте [Discord Developer Portal](https://discord.com/developers/applications).
2. Нажмите **New Application**, назовите бота (например, `TeamGrief Support`) и нажмите **Create**.
3. Перейдите во вкладку **Bot** слева.
4. Нажмите **Reset Token** и скопируйте токен.
5. *(Опционально)* Включите **Server Members Intent** и **Message Content Intent**, если планируете включить их в конфиге.

### 2. Заполнение `config.json`
Откройте файл [`config.json`](file:///C:/Users/dinot/.gemini/antigravity/scratch/teamgrief_ticket_bot/config.json):

```json
{
  "token": "СЮДА_ТОКЕН_БОТА",
  "prefix": "!",
  "guild_id": 0,
  "support_role_id": 0,
  "ticket_category_id": 0,
  "closed_category_id": 0,
  "log_channel_id": 0,
  "sync_commands": true,
  "privileged_intents": false
}
```

* **`token`**: Токен вашего бота Discord.
* **`guild_id`**: ID вашего Discord-сервера. Если указан, слэш-команды обновляются мгновенно на сервере. Если `0`, регистрация идёт глобально.
* **`support_role_id`**: ID роли техподдержки/модератора TeamGrief (у них будет доступ ко всем создаваемым тикетам).
* **`ticket_category_id`**: ID категории для активных тикетов (если `0`, создастся категория `🎫・TICKETS・⚔️`).
* **`closed_category_id`**: ID категории для архива (если `0`, создастся `🔒・CLOSED TICKETS・📁`).
* **`log_channel_id`**: ID текстового канала для отправки транскриптов закрытых тикетов (если `0`, логирование в канал отключено).

### 3. Запуск на Windows
1. Убедитесь, что установлен Python 3.10+ и зависимости:
   ```bash
   pip install -r requirements.txt
   ```
2. Запустите двойным кликом файл [`start_bot.bat`](file:///C:/Users/dinot/.gemini/antigravity/scratch/teamgrief_ticket_bot/start_bot.bat) или выполните команду:
   ```bash
   python bot.py
   ```
3. При запуске бот выведет в консоль ссылку-приглашение на сервер. Перейдите по ней и добавьте бота.

### 4. Установка фирменной аватарки TeamGrief
В корень проекта уже сохранён официальный логотип [`avatar.png`](file:///C:/Users/dinot/.gemini/antigravity/scratch/teamgrief_ticket_bot/avatar.png).

Установить его боту можно любым из способов:
* **Автоматически через скрипт**: запустите `python set_avatar.py` (токен должен быть указан в `config.json`).
* **Через команду в Discord**: напишите `!setavatar` в чате с правами администратора.
* **Вручную**: загрузите `avatar.png` во вкладке **Bot -> Icon** на [Discord Developer Portal](https://discord.com/developers/applications).

### 5. Отправка панели на сервер
- В нужном текстовом канале напишите слэш-команду:
  ```
  /ticket-panel
  ```
- Либо запустите утилиту:
  ```bash
  python send_panel.py
  ```

import asyncio
import os
import discord
from discord import app_commands
from discord.ext import commands
from utils.transcript import generate_html_transcript

TEAMGRIEF_COLOR = discord.Color.from_rgb(245, 166, 35)  # Фирменный золотистый цвет логотипа TeamGrief

# ID основных ролей персонала сервера TeamGrief
DEFAULT_STAFF_ROLE_IDS = [
    1543281337908199567,  # ・Команда проекта
    1543281337858002958,  # ・Администратор
    1543281337858002962,  # ・Куратор
    1563827384409391104,  # ・Технический Администратор
    1563527398396395630,  # ・Главный Администратор
    1563527515946098820,  # ・Владелец
]


class TicketReasonModal(discord.ui.Modal, title="TeamGrief >> Создание обращения"):
    topic = discord.ui.TextInput(
        label="Тема обращения",
        placeholder="Например: Пропал донат / Баг на сервере / Краш",
        max_length=100,
        required=True
    )
    details = discord.ui.TextInput(
        label="Подробное описание проблемы",
        style=discord.TextStyle.paragraph,
        placeholder="Опишите ситуацию, укажите игровой никнейм и важные подробности...",
        max_length=1500,
        required=True
    )

    def __init__(self, cog, category_name: str):
        super().__init__()
        self.cog = cog
        self.category_name = category_name

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        await self.cog.create_ticket_channel(
            interaction=interaction,
            category_name=self.category_name,
            topic=self.topic.value,
            details=self.details.value
        )


class MediaApplicationModal(discord.ui.Modal, title="TeamGrief >> Заявка на Медиа"):
    channel_url = discord.ui.TextInput(
        label="Ссылка на ваш канал / соцсеть",
        placeholder="https://youtube.com/@... или twitch.tv/... или tiktok/...",
        max_length=150,
        required=True
    )
    subscribers = discord.ui.TextInput(
        label="Количество подписчиков",
        placeholder="Например: 100",
        max_length=50,
        required=True
    )
    views = discord.ui.TextInput(
        label="Среднее количество просмотров",
        placeholder="Например: 500",
        max_length=50,
        required=True
    )

    def __init__(self, cog):
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        details = (
            f"**Канал:** {self.channel_url.value}\n"
            f"**Подписчики:** {self.subscribers.value}\n"
            f"**Просмотры:** {self.views.value}"
        )
        await self.cog.create_ticket_channel(
            interaction=interaction,
            category_name="Заявка на Медиа",
            topic=f"Медиа-заявка от {interaction.user}",
            details=details,
            is_media=True
        )


class TicketLauncherView(discord.ui.View):
    """Постоянная интерактивная панель создания тикетов в стиле TeamGrief."""
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.select(
        custom_id="teamgrief_ticket_select",
        placeholder="Выберите раздел для обращения в поддержку...",
        min_values=1,
        max_values=1,
        options=[
            discord.SelectOption(
                label="Техническая помощь / Баги",
                value="tech_support",
                description="Ошибки при игре, вылеты, баги сервера или клиента",
                emoji="🛠️"
            ),
            discord.SelectOption(
                label="Покупка / Донат / Привилегии",
                value="billing_support",
                description="Вопросы оплаты, выдача доната, проблемы с чеком",
                emoji="💵"
            ),
            discord.SelectOption(
                label="Вопрос к Администрации / Жалоба",
                value="other_report",
                description="Личный вопрос руководству или конфиденциальная жалоба",
                emoji="❗"
            ),
        ]
    )
    async def select_category(self, interaction: discord.Interaction, select: discord.ui.Select):
        selected_value = select.values[0]
        categories = {
            "tech_support": "Техническая помощь / Баги",
            "billing_support": "Покупка / Донат",
            "other_report": "Вопрос к Администрации"
        }
        category_name = categories.get(selected_value, "Поддержка")
        modal = TicketReasonModal(cog=self.cog, category_name=category_name)
        await interaction.response.send_modal(modal)


class ManageMemberModal(discord.ui.Modal):
    def __init__(self, cog, action: str):
        title = "Добавить в тикет" if action == "add" else "Исключить из тикета"
        super().__init__(title=title)
        self.cog = cog
        self.action = action

        self.user_input = discord.ui.TextInput(
            label="ID пользователя или @упоминание",
            placeholder="Например: 123456789012345678",
            min_length=3,
            max_length=32,
            required=True
        )
        self.add_item(self.user_input)

    async def on_submit(self, interaction: discord.Interaction):
        raw_val = self.user_input.value.strip().replace("<@", "").replace(">", "").replace("!", "")
        try:
            user_id = int(raw_val)
            member = interaction.guild.get_member(user_id) or await interaction.guild.fetch_member(user_id)
        except Exception:
            await interaction.response.send_message("❌ Не удалось найти пользователя по указанному ID.", ephemeral=True)
            return

        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel):
            return

        if self.action == "add":
            await channel.set_permissions(member, view_channel=True, send_messages=True, read_message_history=True, attach_files=True)
            await interaction.response.send_message(f"✅ Пользователь {member.mention} добавлен в тикет.")
        else:
            await channel.set_permissions(member, overwrite=None)
            await interaction.response.send_message(f"🚫 Пользователь {member.mention} исключён из тикета.")


class TicketControlView(discord.ui.View):
    """Постоянная панель управления внутри тикет-канала TeamGrief."""
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(
        label="Закрыть тикет",
        style=discord.ButtonStyle.danger,
        emoji="🔒",
        custom_id="tg_btn_close"
    )
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        confirm_view = TicketCloseConfirmView(self.cog)
        await interaction.response.send_message(
            "❓ Вы уверены, что хотите закрыть это обращение? История переписки будет сохранена в транскрипт.",
            view=confirm_view,
            ephemeral=True
        )

    @discord.ui.button(
        label="Транскрипт",
        style=discord.ButtonStyle.secondary,
        emoji="📜",
        custom_id="tg_btn_transcript"
    )
    async def transcript_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        if not isinstance(interaction.channel, discord.TextChannel):
            return
        transcript_file = await generate_html_transcript(interaction.channel)
        discord_file = discord.File(fp=transcript_file, filename=f"transcript-{interaction.channel.name}.html")
        await interaction.followup.send(
            content="📄 Транскрипт тикета TeamGrief:",
            file=discord_file,
            ephemeral=True
        )

    @discord.ui.button(
        label="Добавить участника",
        style=discord.ButtonStyle.primary,
        emoji="➕",
        custom_id="tg_btn_add_member"
    )
    async def add_member_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ManageMemberModal(self.cog, action="add"))

    @discord.ui.button(
        label="Удалить участника",
        style=discord.ButtonStyle.secondary,
        emoji="➖",
        custom_id="tg_btn_remove_member"
    )
    async def remove_member_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ManageMemberModal(self.cog, action="remove"))


class TicketCloseConfirmView(discord.ui.View):
    """Подтверждение закрытия тикета."""
    def __init__(self, cog):
        super().__init__(timeout=60)
        self.cog = cog

    @discord.ui.button(
        label="Да, закрыть",
        style=discord.ButtonStyle.danger,
        emoji="✅",
        custom_id="tg_btn_confirm_close"
    )
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        await self.cog.close_ticket(interaction.channel, closed_by=interaction.user)

    @discord.ui.button(
        label="Отмена",
        style=discord.ButtonStyle.secondary,
        emoji="❌",
        custom_id="tg_btn_cancel_close"
    )
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="❌ Закрытие тикета отменено.", view=None)


class TicketClosedControlView(discord.ui.View):
    """Постоянная панель управления закрытым тикетом в категории архива (без удаления)."""
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(
        label="Транскрипт",
        style=discord.ButtonStyle.secondary,
        emoji="📜",
        custom_id="tg_btn_closed_transcript"
    )
    async def transcript_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        if not isinstance(interaction.channel, discord.TextChannel):
            return
        transcript_file = await generate_html_transcript(interaction.channel)
        discord_file = discord.File(fp=transcript_file, filename=f"transcript-{interaction.channel.name}.html")
        await interaction.followup.send(
            content="📄 Транскрипт закрытого тикета:",
            file=discord_file,
            ephemeral=True
        )

    @discord.ui.button(
        label="Открыть заново",
        style=discord.ButtonStyle.success,
        emoji="🔓",
        custom_id="tg_btn_reopen"
    )
    async def reopen_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        await self.cog.reopen_ticket(interaction.channel, reopened_by=interaction.user)


class TicketsCog(commands.Cog, name="Tickets"):
    def __init__(self, bot: commands.Bot, config: dict):
        self.bot = bot
        self.config = config

    async def cog_load(self):
        # Регистрируем постоянные Views для бесперебойной работы кнопок 24/7
        self.bot.add_view(TicketLauncherView(self))
        self.bot.add_view(TicketControlView(self))
        self.bot.add_view(TicketClosedControlView(self))

    async def get_or_create_category(self, guild: discord.Guild) -> discord.CategoryChannel:
        cat_id = self.config.get("ticket_category_id", 0)
        if cat_id and int(cat_id) != 0:
            cat = guild.get_channel(int(cat_id))
            if isinstance(cat, discord.CategoryChannel):
                return cat

        for cat in guild.categories:
            if "тикет" in cat.name.lower() and "архив" not in cat.name.lower() and "closed" not in cat.name.lower():
                return cat
            if "ticket" in cat.name.lower() and "closed" not in cat.name.lower():
                return cat

        # Категория в фирменном стиле сервера: Emoji >> Название
        return await guild.create_category("🎫 >> Тикеты")

    async def get_closed_category(self, guild: discord.Guild) -> discord.CategoryChannel:
        cat_id = self.config.get("closed_category_id", 0)
        if cat_id and int(cat_id) != 0:
            cat = guild.get_channel(int(cat_id))
            if isinstance(cat, discord.CategoryChannel):
                return cat

        for cat in guild.categories:
            if "архив" in cat.name.lower() or "closed" in cat.name.lower() or "закрыт" in cat.name.lower():
                return cat

        # Архивная категория в стиле сервера
        return await guild.create_category("🔒 >> Архив тикетов")

    async def create_ticket_channel(self, interaction: discord.Interaction, category_name: str, topic: str, details: str, is_media: bool = False):
        guild = interaction.guild
        user = interaction.user

        if not guild:
            await interaction.followup.send("Команда доступна только на сервере.", ephemeral=True)
            return

        # Проверка на наличие уже открытого тикета у пользователя
        uname_prefix = user.name.lower()[:8]
        for ch in guild.text_channels:
            ch_name_clean = ch.name.lower()
            is_closed = "🔒" in ch.name or "closed" in ch_name_clean or (ch.category and "архив" in ch.category.name.lower())
            if not is_closed and uname_prefix in ch_name_clean and ("🎫" in ch.name or "🎬" in ch.name or "tg-" in ch_name_clean):
                await interaction.followup.send(
                    f"⚠️ У вас уже есть открытый канал: {ch.mention}. Пожалуйста, используйте его.",
                    ephemeral=True
                )
                return

        category = await self.get_or_create_category(guild)

        # Базовые права: канал скрыт для всех, виден автору и боту
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            guild.me: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_channels=True,
                attach_files=True,
                embed_links=True
            ),
            user: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True,
                embed_links=True
            )
        }

        # Выдаем права ролям персонала сервера TeamGrief
        staff_ids = list(DEFAULT_STAFF_ROLE_IDS)
        cfg_role = self.config.get("support_role_id", 0)
        if cfg_role and int(cfg_role) != 0 and int(cfg_role) not in staff_ids:
            staff_ids.append(int(cfg_role))

        for rid in staff_ids:
            role = guild.get_role(rid)
            if role:
                overwrites[role] = discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True,
                    attach_files=True,
                    embed_links=True
                )

        # Формат имени канала в точности как на сервере: │ Эмодзи・название
        clean_username = "".join(c for c in user.name.lower() if c.isalnum() or c in ("-", "_"))[:10]
        channel_name = f"│🎬・{clean_username}" if is_media else f"│🎫・{clean_username}"

        channel = await guild.create_text_channel(
            name=channel_name,
            category=category,
            overwrites=overwrites,
            topic=f"TeamGrief | {category_name}: {user} | ID: {user.id}"
        )

        if is_media:
            embed = discord.Embed(
                title="🎬 >> TeamGrief | Заявка на Медиа",
                description=(
                    f"Приветствуем, {user.mention}!\n\n"
                    f"Ваша заявка на получение **Медиа-статуса** на проекте **TeamGrief** успешно зарегистрирована.\n"
                    f"Смотрящие и кураторы медиа ознакомятся с вашей анкетой и дадут ответ прямо здесь.\n\n"
                    f"**Данные анкеты:**\n"
                    f"{details}\n"
                ),
                color=discord.Color.gold()
            )
            embed.set_footer(text="TeamGrief >> Медиа-команда • Ожидайте рассмотрения")
        else:
            embed = discord.Embed(
                title=f"🎫 >> TeamGrief | {category_name}",
                description=(
                    f"Приветствуем, {user.mention}!\n\n"
                    f"Ваше обращение принято **Командой проекта TeamGrief**.\n"
                    f"Пожалуйста, подробно опишите все детали, приложите скриншоты или логи.\n"
                    f"Персонал проекта ответит вам в ближайшее время!\n\n"
                    f"**Детали тикета:**\n"
                    f"│ 👤・**Автор:** {user.mention} (`{user.id}`)\n"
                    f"│ 📌・**Раздел:** `{category_name}`\n"
                    f"│ 📋・**Тема:** {topic}\n"
                    f"│ 📝・**Описание:** {details}\n"
                ),
                color=TEAMGRIEF_COLOR
            )
            embed.set_footer(text="TeamGrief >> Самый чиловый проект • Используйте кнопки ниже")

        mention_str = f"{user.mention}"
        view = TicketControlView(self)
        await channel.send(content=mention_str, embed=embed, view=view)

        await interaction.followup.send(
            f"✅ Ваш тикет успешно создан: {channel.mention}",
            ephemeral=True
        )

    async def close_ticket(self, channel: discord.TextChannel, closed_by: discord.Member | discord.User):
        await channel.send(f"🔒 Тикет закрывается пользователем {closed_by.mention}. Перемещение в архив...")

        # 1. Перемещение в категорию архива и переименование канала
        closed_category = await self.get_closed_category(channel.guild)
        clean_name = channel.name.replace("│", "").replace("🎫", "").replace("🎬", "").replace("🔒", "").replace("・", "").replace("tg-", "").replace("media-", "").replace("closed-", "").strip()
        new_channel_name = f"│🔒・{clean_name[:10]}"
        try:
            # Перемещаем без sync_permissions чтобы не требовать Manage Roles
            await channel.edit(category=closed_category, name=new_channel_name)
        except Exception:
            try:
                await channel.edit(category=closed_category)
            except Exception:
                pass

        # 2. Мгновенно скрываем канал от автора и обычных участников
        for target in list(channel.overwrites.keys()):
            if isinstance(target, discord.Member) and not target.bot:
                try:
                    await channel.set_permissions(target, view_channel=False, send_messages=False)
                except Exception:
                    pass

        # 3. Генерация транскрипта
        transcript_buffer = await generate_html_transcript(channel)
        filename = f"transcript-{channel.name}.html"

        # Отправка в лог-канал
        log_channel_id = self.config.get("log_channel_id", 0)
        if log_channel_id and int(log_channel_id) != 0:
            log_channel = channel.guild.get_channel(int(log_channel_id))
            if isinstance(log_channel, discord.TextChannel):
                transcript_buffer.seek(0)
                log_file = discord.File(fp=transcript_buffer, filename=filename)
                log_embed = discord.Embed(
                    title=f"🔒 Тикет закрыт: #{channel.name}",
                    description=f"│ 👤・**Закрыл:** {closed_by.mention}\n"
                                f"│ 🌐・**Сервер:** {channel.guild.name}\n"
                                f"│ 📄・**Канал:** `#{channel.name}`\n",
                    color=discord.Color.red()
                )
                if channel.topic:
                    log_embed.add_field(name="Инфо", value=channel.topic, inline=False)
                await log_channel.send(embed=log_embed, file=log_file)

        # Отправка в ЛС автору тикета
        for target, overwrite in channel.overwrites.items():
            if isinstance(target, discord.Member) and not target.bot and target.id != closed_by.id:
                try:
                    transcript_buffer.seek(0)
                    dm_file = discord.File(fp=transcript_buffer, filename=filename)
                    await target.send(
                        f"Ваше обращение на сервере **TeamGrief** ({channel.guild.name}) было закрыто модератором {closed_by}.\n"
                        f"История переписки сохранена в транскрипте ниже:",
                        file=dm_file
                    )
                except Exception:
                    pass

        # 4. Сообщение в архивном канале с кнопками управления (без кнопки удаления)
        closed_embed = discord.Embed(
            title="🔒 >> Тикет сохранён в архив",
            description=(
                f"Обращение закрыто пользователем {closed_by.mention}.\n"
                f"Канал успешно перемещён в архивную категорию **`{closed_category.name}`** и будет храниться здесь.\n"
                f"Обычные пользователи больше не видят этот канал.\n\n"
                f"│ 📜・Нажмите **Транскрипт**, чтобы скачать файл диалога.\n"
                f"│ 🔓・Нажмите **Открыть заново**, если требуется возобновить обращение.\n"
            ),
            color=discord.Color.dark_gray()
        )
        closed_embed.set_footer(text="TeamGrief >> Архив тикетов")
        view = TicketClosedControlView(self)
        await channel.send(embed=closed_embed, view=view)

    async def reopen_ticket(self, channel: discord.TextChannel, reopened_by: discord.Member | discord.User):
        open_category = await self.get_or_create_category(channel.guild)
        clean_name = channel.name.replace("│", "").replace("🔒", "").replace("🎫", "").replace("🎬", "").replace("・", "").strip()
        new_name = f"│🎫・{clean_name[:10]}"

        try:
            await channel.edit(category=open_category, name=new_name)
        except Exception:
            pass

        # Восстанавливаем права автору
        for target, overwrite in channel.overwrites.items():
            if isinstance(target, discord.Member) and not target.bot:
                try:
                    await channel.set_permissions(target, send_messages=True, view_channel=True, read_message_history=True, attach_files=True)
                except Exception:
                    pass

        reopen_embed = discord.Embed(
            title="🔓 >> Тикет снова открыт",
            description=f"Тикет был открыт заново пользователем {reopened_by.mention}!\n"
                        f"Канал возвращён в категорию активных тикетов **`{open_category.name}`**.",
            color=TEAMGRIEF_COLOR
        )
        view = TicketControlView(self)
        await channel.send(embed=reopen_embed, view=view)

    @app_commands.command(name="ticket-panel", description="Отправить панель тикетов TeamGrief в текущий канал")
    @app_commands.default_permissions(administrator=True)
    async def ticket_panel_command(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="📌 >> TeamGrief | Центр поддержки",
            description=(
                "Добро пожаловать в центр поддержки сервера **TeamGrief >> Самый чиловый проект**!\n\n"
                "Возникли вопросы по донату, технические сложности, краши или хотите предложить идею? "
                "Создайте приватное обращение к персоналу проекта.\n\n"
                "**Правила подачи тикета:**\n"
                "│ 📌・Формулируйте вопрос четко, понятно и без лишнего спама.\n"
                "│ 📎・Прикрепляйте скриншоты, чеки или логи при наличии.\n"
                "│ ⏳・Специалисты ответят вам в порядке очереди прямо в канале тикета.\n\n"
                "⬇️ **Для создания тикета выберите нужный раздел в меню ниже:**"
            ),
            color=TEAMGRIEF_COLOR
        )
        embed.set_footer(text="TeamGrief >> Поддержка • Выберите раздел в меню ⬇️")

        view = TicketLauncherView(self)
        await interaction.channel.send(embed=embed, view=view)
        await interaction.response.send_message("✅ Панель тикетов TeamGrief успешно отправлена в канал!", ephemeral=True)

    @app_commands.command(name="ticket-add", description="Добавить пользователя в текущий тикет")
    async def ticket_add_command(self, interaction: discord.Interaction, member: discord.Member):
        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel) or not ("🎫" in channel.name or "🎬" in channel.name or "tg-" in channel.name or "ticket" in channel.name):
            await interaction.response.send_message("❌ Эта команда может использоваться только внутри тикета.", ephemeral=True)
            return

        await channel.set_permissions(member, view_channel=True, send_messages=True, read_message_history=True, attach_files=True)
        await interaction.response.send_message(f"✅ Пользователь {member.mention} добавлен в тикет.")

    @app_commands.command(name="ticket-remove", description="Исключить пользователя из текущего тикета")
    async def ticket_remove_command(self, interaction: discord.Interaction, member: discord.Member):
        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel) or not ("🎫" in channel.name or "🎬" in channel.name or "tg-" in channel.name or "ticket" in channel.name):
            await interaction.response.send_message("❌ Эта команда может использоваться только внутри тикета.", ephemeral=True)
            return

        await channel.set_permissions(member, overwrite=None)
        await interaction.response.send_message(f"🚫 Пользователь {member.mention} удален из тикета.")

    @app_commands.command(name="ticket-close", description="Закрыть текущий тикет")
    async def ticket_close_command(self, interaction: discord.Interaction):
        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel) or not ("🎫" in channel.name or "🎬" in channel.name or "tg-" in channel.name or "ticket" in channel.name):
            await interaction.response.send_message("❌ Эта команда может использоваться только внутри тикета.", ephemeral=True)
            return

        confirm_view = TicketCloseConfirmView(self)
        await interaction.response.send_message(
            "❓ Вы уверены, что хотите закрыть это обращение?",
            view=confirm_view,
            ephemeral=True
        )


async def setup(bot: commands.Bot):
    cog = TicketsCog(bot, bot.config)
    await bot.add_cog(cog)

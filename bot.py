import asyncio
import json
import logging
import os
import sys
import discord
from discord.ext import commands

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("TeamGrief-Bot")

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")


def load_config() -> dict:
    cfg = {}
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception as e:
            logger.warning(f"Не удалось прочитать config.json: {e}")

    # Значения по умолчанию
    cfg.setdefault("prefix", "!")
    cfg.setdefault("guild_id", 0)
    cfg.setdefault("support_role_id", 0)
    cfg.setdefault("ticket_category_id", 0)
    cfg.setdefault("closed_category_id", 0)
    cfg.setdefault("log_channel_id", 0)
    cfg.setdefault("sync_commands", True)
    cfg.setdefault("privileged_intents", False)

    # Переменные окружения (приоритет для хостингов)
    if os.getenv("DISCORD_TOKEN"):
        cfg["token"] = os.getenv("DISCORD_TOKEN")
    elif os.getenv("TOKEN"):
        cfg["token"] = os.getenv("TOKEN")

    if os.getenv("GUILD_ID"):
        try:
            cfg["guild_id"] = int(os.getenv("GUILD_ID"))
        except ValueError:
            pass

    if os.getenv("SUPPORT_ROLE_ID"):
        try:
            cfg["support_role_id"] = int(os.getenv("SUPPORT_ROLE_ID"))
        except ValueError:
            pass

    if os.getenv("TICKET_CATEGORY_ID"):
        try:
            cfg["ticket_category_id"] = int(os.getenv("TICKET_CATEGORY_ID"))
        except ValueError:
            pass

    if os.getenv("CLOSED_CATEGORY_ID"):
        try:
            cfg["closed_category_id"] = int(os.getenv("CLOSED_CATEGORY_ID"))
        except ValueError:
            pass

    if os.getenv("LOG_CHANNEL_ID"):
        try:
            cfg["log_channel_id"] = int(os.getenv("LOG_CHANNEL_ID"))
        except ValueError:
            pass

    return cfg


class TeamGriefBot(commands.Bot):
    def __init__(self, config: dict):
        self.config = config

        intents = discord.Intents.default()
        if config.get("privileged_intents", False):
            intents.message_content = True
            intents.members = True

        super().__init__(
            command_prefix=config.get("prefix", "!"),
            intents=intents,
            help_command=None
        )

    async def setup_hook(self):
        # Загрузка кога тикетов
        await self.load_extension("cogs.tickets")
        logger.info("Модуль cogs.tickets успешно загружен.")

        # Синхронизация слэш-команд
        if self.config.get("sync_commands", True):
            guild_id = self.config.get("guild_id", 0)
            if guild_id and int(guild_id) != 0:
                guild = discord.Object(id=int(guild_id))
                self.tree.copy_global_to(guild=guild)
                synced = await self.tree.sync(guild=guild)
                logger.info(f"Синхронизировано {len(synced)} слэш-команд для сервера ID: {guild_id}")
            else:
                synced = await self.tree.sync()
                logger.info(f"Глобально синхронизировано {len(synced)} слэш-команд.")

    async def on_ready(self):
        logger.info("=" * 60)
        logger.info(f"Бот TeamGrief запущен как: {self.user} (ID: {self.user.id})")
        logger.info(f"Серверов: {len(self.guilds)}")

        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name="TeamGrief | /ticket-panel"
        )
        await self.change_presence(status=discord.Status.online, activity=activity)

        permissions = discord.Permissions(
            manage_channels=True,
            send_messages=True,
            embed_links=True,
            attach_files=True,
            read_message_history=True,
            view_channel=True,
            use_application_commands=True
        )
        invite_url = discord.utils.oauth_url(self.user.id, permissions=permissions)
        logger.info("Ссылка для приглашения бота на сервер:")
        logger.info(invite_url)
        logger.info("=" * 60)


async def main():
    config = load_config()
    token = config.get("token", "").strip()

    if not token or token == "YOUR_BOT_TOKEN_HERE":
        logger.error("=" * 60)
        logger.error("ОШИБКА: Токен бота TeamGrief не указан в config.json!")
        logger.error("Откройте config.json и вставьте ваш токен Discord бота в поле 'token'.")
        logger.error("=" * 60)
        sys.exit(1)

    bot = TeamGriefBot(config)

    # Добавляем текстовые команды управления для администратора
    @bot.command(name="sync")
    @commands.has_permissions(administrator=True)
    async def sync_cmd(ctx):
        guild_id = config.get("guild_id", 0)
        if guild_id and int(guild_id) != 0:
            guild = discord.Object(id=int(guild_id))
            bot.tree.copy_global_to(guild=guild)
            synced = await bot.tree.sync(guild=guild)
            await ctx.send(f"✅ Синхронизировано {len(synced)} слэш-команд для сервера {guild_id}.")
        else:
            synced = await bot.tree.sync()
            await ctx.send(f"✅ Глобально синхронизировано {len(synced)} слэш-команд.")

    @bot.command(name="setavatar")
    @commands.has_permissions(administrator=True)
    async def setavatar_cmd(ctx):
        avatar_path = os.path.join(os.path.dirname(__file__), "avatar.png")
        if not os.path.exists(avatar_path):
            await ctx.send("❌ Файл avatar.png не найден в папке бота.")
            return
        try:
            with open(avatar_path, "rb") as f:
                await bot.user.edit(avatar=f.read())
            await ctx.send("✅ Аватарка бота TeamGrief успешно обновлена на официальный логотип!")
        except discord.HTTPException as e:
            if e.status == 429:
                await ctx.send("⚠️ Превышен лимит запросов Discord на смену аватара. Попробуйте через 10-15 минут.")
            else:
                await ctx.send(f"❌ Ошибка обновления аватарки: {e}")
        except Exception as e:
            await ctx.send(f"❌ Ошибка: {e}")

    async with bot:
        await bot.start(token)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем.")

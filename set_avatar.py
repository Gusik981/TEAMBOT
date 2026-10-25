import asyncio
import json
import os
import sys
import discord

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")
AVATAR_PATH = os.path.join(os.path.dirname(__file__), "avatar.png")


def get_token():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f).get("token")
        except Exception:
            pass
    return os.getenv("DISCORD_TOKEN") or os.getenv("TOKEN")


async def main():
    token = get_token()
    if not token or token == "YOUR_BOT_TOKEN_HERE":
        print("❌ Ошибка: Укажите действительный токен бота в файле config.json!")
        sys.exit(1)

    if not os.path.exists(AVATAR_PATH):
        print("❌ Ошибка: Файл avatar.png не найден в папке бота!")
        sys.exit(1)

    with open(AVATAR_PATH, "rb") as f:
        avatar_bytes = f.read()

    intents = discord.Intents.default()
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        print(f"Подключен к Discord как: {client.user} (ID: {client.user.id})")
        print("Отправка новой аватарки в Discord API...")
        try:
            await client.user.edit(avatar=avatar_bytes)
            print("✅ УСПЕХ: Аватарка бота TeamGrief успешно установлена!")
        except discord.HTTPException as e:
            if e.status == 429:
                print("⚠️ Превышен лимит запросов Discord на смену аватара. Попробуйте через 10-15 минут.")
            else:
                print(f"❌ Ошибка при смене аватарки: {e}")
        finally:
            await client.close()

    await client.start(token)


if __name__ == "__main__":
    asyncio.run(main())

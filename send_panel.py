import asyncio
import json
import os
import sys
import discord

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from cogs.tickets import TicketLauncherView, TEAMGRIEF_COLOR

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")

def load_token():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
            return cfg.get("token")
    return os.getenv("DISCORD_TOKEN") or os.getenv("TOKEN")

TOKEN = load_token()

intents = discord.Intents.default()
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f"Подключен как: {client.user}")
    
    target_channel = None

    for guild in client.guilds:
        print(f"\nСервер: {guild.name} (ID: {guild.id})")
        print("\nКаналы:")
        for ch in guild.text_channels:
            print(f" - #{ch.name} (ID: {ch.id})")
            if "ticket" in ch.name.lower() or "тикет" in ch.name.lower():
                target_channel = ch

    if target_channel:
        print(f"\nНайден целевой канал для тикетов: #{target_channel.name} (ID: {target_channel.id})")
        
        embed = discord.Embed(
            title="⚔️ TeamGrief | Центр поддержки",
            description="Возникли сложности с запуском, баги, вопросы по подписке или предложения по улучшению **TeamGrief**?\n\n"
                        "Выберите нужный раздел в выпадающем меню ниже, заполните короткую форму, и команда поддержки свяжется с вами!\n\n"
                        "**Правила:**\n"
                        "• Формулируйте проблему четко и развернуто.\n"
                        "• Прикрепляйте логи краша или скриншоты при наличии.\n"
                        "• Не создавайте несколько тикетов по одной проблеме — это ускорит ответ.",
            color=TEAMGRIEF_COLOR
        )
        embed.set_footer(text="TeamGrief Support • Выберите категорию в меню ниже ⬇️")

        view = TicketLauncherView(None)
        msg = await target_channel.send(embed=embed, view=view)
        print(f"УСПЕХ! Панель тикетов отправлена в #{target_channel.name}! ID сообщения: {msg.id}")
    else:
        print("Канал со словом 'ticket' или 'тикет' не найден. Создайте канал или отправьте через слэш-команду /ticket-panel.")

    await client.close()

if __name__ == "__main__":
    if not TOKEN or TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("Укажите токен в config.json перед запуском send_panel.py!")
        sys.exit(1)
    asyncio.run(client.start(TOKEN))

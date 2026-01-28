import asyncio
import threading
import uvicorn
import os
from tbot import app as telegram_app # Asegúrate de que tu archivo del bot se llame tbot.py
from main import app as fastapi_app

def run_bot():
    print("🚀 Iniciando Bot de Telegram...")
    telegram_app.run_polling(close_loop=False)

if __name__ == "__main__":
    # 1. Ejecutar el bot en un hilo separado
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()

    # 2. Ejecutar FastAPI en el hilo principal
    port = int(os.getenv("PORT", 10000))
    uvicorn.run(fastapi_app, host="0.0.0.0", port=port)
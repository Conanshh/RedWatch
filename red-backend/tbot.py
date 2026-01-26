import asyncio
import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from main import obtener_tiempos 

# Configuración de logs
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

TOKEN = os.getenv("TELEGRAM_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await update.message.reply_text(
            "🚌 ¡RedWatch Bot Activo!\n\n"
            "Comandos:\n"
            "/p [paradero] - Monitoreo cada 45s\n"
            "/stop - Detener monitoreo"
        )

async def monitor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Verificación de seguridad para el editor (evita errores de None)
    if not update.effective_chat or not update.message or context.user_data is None:
        return

    if not context.args:
        await update.message.reply_text("❌ Indica un paradero. Ejemplo: /p PB719")
        return

    paradero = context.args[0].upper()
    chat_id = update.effective_chat.id
    
    # Marcamos como activo
    context.user_data['activo'] = True
    await update.message.reply_text(f"📡 Monitoreando {paradero}... Te avisaré cada cierto tiempo.")

    # Ciclo de monitoreo
    while context.user_data.get('activo'):
        try:
            datos = await obtener_tiempos(paradero)
            # Enviamos el mensaje directamente al chat_id
            await context.bot.send_message(chat_id=chat_id, text=datos['notificacion'])
            
            # Espera de X segundos
            await asyncio.sleep(20) 
            
            # Verificamos si sigue activo después de la espera
            if not context.user_data.get('activo'):
                break
                
        except Exception as e:
            logging.error(f"Error en bot: {e}")
            await context.bot.send_message(chat_id=chat_id, text="⚠️ Hubo un error en la consulta. Reintenta en breve.")
            break

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data is not None:
        context.user_data['activo'] = False
        
    if update.message:
        await update.message.reply_text("🛑 Monitoreo detenido.")

if __name__ == '__main__':
    if not TOKEN:
        print("❌ Error: Variable TELEGRAM_TOKEN no configurada.")
    else:
        app = ApplicationBuilder().token(TOKEN).build()
        
        # Comandos
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("p", monitor))
        app.add_handler(CommandHandler("stop", stop))
        
        print("🚀 Bot de Telegram en marcha...")
        app.run_polling()
import asyncio
import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from main import obtener_tiempos 

# Configuración de logs para Render
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

TOKEN = os.getenv("TELEGRAM_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await update.message.reply_text(
            "🚌 *¡RedWatch Bot Activo!*\n\n"
            "Usa `/p [paradero]` para empezar.\n"
            "Te avisaré cada *20 segundos*.",
            parse_mode='Markdown'
        )

async def monitor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_chat or not update.message or context.user_data is None:
        return

    if not context.args:
        await update.message.reply_text("❌ Indica un paradero. Ejemplo: `/p PB719`", parse_mode='Markdown')
        return

    paradero = context.args[0].upper()
    chat_id = update.effective_chat.id
    context.user_data['activo'] = True
    
    await update.message.reply_text(f"🔍 Buscando micros en *{paradero}*...", parse_mode='Markdown')

    while context.user_data.get('activo'):
        try:
            # Feedback Visual: Aparecerá "bot está escribiendo..." en Telegram
            await context.bot.send_chat_action(chat_id=chat_id, action="typing")
            
            datos = await obtener_tiempos(paradero)
            
            # Enviamos la notificación (usando Markdown para que resalten los minutos)
            texto = datos['notificacion'].replace("min", "*min*") # Pone los minutos en negrita
            await context.bot.send_message(chat_id=chat_id, text=texto, parse_mode='Markdown')
            
            # Feedback de espera en consola de Render
            logging.info(f"Esperando 20s para {paradero}")
            
            # Tiempo ajustado a 20 segundos
            await asyncio.sleep(20) 
            
            if not context.user_data.get('activo'):
                break
                
        except Exception as e:
            logging.error(f"Error en bot: {e}")
            # Si hay error, avisamos pero no matamos el bot, reintentamos en 10s
            await context.bot.send_message(chat_id=chat_id, text="⚠️ Error de conexión con Red. Reintentando...")
            await asyncio.sleep(10)

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data is not None:
        context.user_data['activo'] = False
        
    if update.message:
        await update.message.reply_text("🛑 *Monitoreo detenido.* ¡Buen viaje!", parse_mode='Markdown')

if __name__ == '__main__':
    if not TOKEN:
        # Esto saldrá en los logs de Render si la variable no está cargada
        print("❌ ERROR CRÍTICO: Variable TELEGRAM_TOKEN no encontrada en Environment.")
    else:
        app = ApplicationBuilder().token(TOKEN).build()
        
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("p", monitor))
        app.add_handler(CommandHandler("stop", stop))
        
        print("🚀 Bot de Telegram en marcha con intervalo de 20s...")
        app.run_polling()
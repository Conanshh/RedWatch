import asyncio
import os
import logging
import psycopg2
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from main import obtener_tiempos 

# Configuración de logs
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO
)

TOKEN = os.getenv("TELEGRAM_TOKEN")
DB_URL = os.getenv("DATABASE_URL")

# --- FUNCIONES DE BASE DE DATOS (NEON) ---

def guardar_fav(user_id: int, alias: str, paradero_id: str):
    conn = None
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
        cur.execute('''
            INSERT INTO favoritos (user_id, alias, paradero_id) 
            VALUES (%s, %s, %s) 
            ON CONFLICT (user_id, alias) DO UPDATE SET paradero_id = EXCLUDED.paradero_id
        ''', (user_id, alias.lower(), paradero_id.upper()))
        conn.commit()
        cur.close()
    except Exception as e:
        logging.error(f"Error guardando favorito: {e}")
    finally:
        if conn: conn.close()

def obtener_favs(user_id: int):
    conn = None
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
        cur.execute('SELECT alias, paradero_id FROM favoritos WHERE user_id = %s', (user_id,))
        rows = cur.fetchall()
        cur.close()
        return {row[0]: row[1] for row in rows}
    except Exception as e:
        logging.error(f"Error obteniendo favoritos: {e}")
        return {}
    finally:
        if conn: conn.close()

# --- COMANDOS DEL BOT ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message: return
    await update.message.reply_text(
        "🚌 *¡RedWatch Pro activado!*\n\n"
        "• `/p casa` - Inicia monitoreo con alias\n"
        "• `/p PB719` - Monitoreo con código directo\n"
        "• `/fav PB719 casa` - Guarda un paradero\n"
        "• `/ver` - Mira tus favoritos\n"
        "• `/stop` - Detener rastreo",
        parse_mode='Markdown'
    )

async def fav(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Validación estricta de mensaje, usuario y argumentos
    if not update.message or not update.effective_user or not context.args or len(context.args) < 2:
        if update.message:
            await update.message.reply_text("❌ Uso: `/fav [código] [nombre]`\nEj: `/fav PB719 casa`")
        return
    
    p_id = context.args[0]
    alias = context.args[1].lower()
    guardar_fav(update.effective_user.id, alias, p_id)
    await update.message.reply_text(f"⭐ Guardado: *{alias}* ➔ `{p_id.upper()}`", parse_mode='Markdown')

async def ver(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_user: return
    
    favs = obtener_favs(update.effective_user.id)
    if not favs:
        await update.message.reply_text("Aún no tienes favoritos. Guarda uno con `/fav`.")
        return
    
    texto = "⭐ *Tus Favoritos:*\n" + "\n".join([f"• *{a}*: `{p}`" for a, p in favs.items()])
    await update.message.reply_text(texto, parse_mode='Markdown')

async def monitor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Validación múltiple para evitar atributos de None
    if (not update.effective_chat or 
        not update.message or 
        not update.effective_user or 
        context.user_data is None or 
        not context.args):
        if update.message and not context.args:
            await update.message.reply_text("❌ Indica un alias o código. Ej: `/p casa` o `/p PB719`", parse_mode='Markdown')
        return

    entrada = context.args[0].lower()
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    favs = obtener_favs(user_id)
    paradero = favs.get(entrada, entrada).upper()
    
    context.user_data['activo'] = True
    await update.message.reply_text(f"📡 Rastreando *{paradero}* ({entrada})...\n_Notificación cada ~35s_", parse_mode='Markdown')

    while context.user_data.get('activo'):
        try:
            # Acción de "typing" para feedback en el reloj/celular
            await context.bot.send_chat_action(chat_id=chat_id, action="typing")
            
            datos = await obtener_tiempos(paradero)
            msg = datos['notificacion'].replace("min", "*min*")
            
            await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode='Markdown')
            
            await asyncio.sleep(20)
            
            # Verificación tras el sleep por si se activó /stop
            if context.user_data is None or not context.user_data.get('activo'): 
                break
                
        except Exception as e:
            logging.error(f"Error en bucle: {e}")
            await asyncio.sleep(10)

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data is not None: 
        context.user_data['activo'] = False
    
    if update.message: 
        await update.message.reply_text("🛑 *Monitoreo detenido.* ¡Buen viaje!", parse_mode='Markdown')

# --- EJECUCIÓN ---

if __name__ == '__main__':
    if not TOKEN or not DB_URL:
        print("❌ Error: Faltan variables de entorno (TELEGRAM_TOKEN o DATABASE_URL).")
    else:
        app = ApplicationBuilder().token(TOKEN).build()
        
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("p", monitor))
        app.add_handler(CommandHandler("fav", fav))
        app.add_handler(CommandHandler("ver", ver))
        app.add_handler(CommandHandler("stop", stop))
        
        print("🚀 Bot RedWatch Pro con validaciones estrictas iniciado...")
        app.run_polling()
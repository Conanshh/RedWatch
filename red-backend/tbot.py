import asyncio
import os
import logging
import psycopg2
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from main import obtener_tiempos 

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

TOKEN = os.getenv("TELEGRAM_TOKEN")
DB_URL = os.getenv("DATABASE_URL")

# --- FUNCIONES DB (NEON) ---
def guardar_fav(user_id: int, alias: str, paradero_id: str) -> None:
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
    except Exception as e:
        logging.error(f"Error DB Guardar: {e}")
    finally:
        if conn: conn.close()

def obtener_favs(user_id: int) -> dict:
    conn = None
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
        cur.execute('SELECT alias, paradero_id FROM favoritos WHERE user_id = %s', (user_id,))
        return {row[0]: row[1] for row in cur.fetchall()}
    except Exception as e:
        logging.error(f"Error DB Obtener: {e}")
        return {}
    finally:
        if conn: conn.close()

# --- LÓGICA DE MONITOREO ---

async def tarea_monitoreo(chat_id: int, user_id: int, paradero: str, context: ContextTypes.DEFAULT_TYPE):
    try:
        while True:
            await context.bot.send_chat_action(chat_id=chat_id, action="typing")
            datos = await obtener_tiempos(paradero)
            
            # Validación estricta del diccionario de la API
            if datos is not None and isinstance(datos, dict):
                notificacion = datos.get('notificacion', 'Sin info.')
                msg = notificacion.replace("min", "*min*")
                await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode='Markdown')
            else:
                await context.bot.send_message(chat_id=chat_id, text="⚠️ Buscando info...")

            for _ in range(20): 
                await asyncio.sleep(1)
                
    except asyncio.CancelledError:
        logging.info(f"Tarea cancelada para {user_id}")
        raise

# --- COMANDOS ---

async def monitor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Validación total de objetos
    if not update.effective_user or not update.effective_chat or not update.message or context.user_data is None:
        return

    # Validación de existencia de argumentos ANTES de acceder a context.args[0]
    if not context.args or len(context.args) < 1:
        await update.message.reply_text("❌ Indica un alias o código. Ej: `/p casa`", parse_mode='Markdown')
        return

    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    entrada = context.args[0].lower()

    if 'tarea_activa' in context.user_data:
        context.user_data['tarea_activa'].cancel()

    favs = obtener_favs(user_id)
    paradero = favs.get(entrada, entrada).upper()
    
    await update.message.reply_text(f"🚀 **Monitoreando:** `{paradero}`\n_Deténlo con /stop_", parse_mode='Markdown')

    task = asyncio.create_task(tarea_monitoreo(chat_id, user_id, paradero, context))
    context.user_data['tarea_activa'] = task

async def fav(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ESCUDO ANTI-NONE: Verificamos longitud antes de tocar context.args
    if not update.effective_user or not update.message:
        return

    if not context.args or len(context.args) < 2:
        await update.message.reply_text("❌ Uso correcto: `/fav [código] [nombre]`\nEjemplo: `/fav PB719 casa`", parse_mode='Markdown')
        return
    
    # Ahora es seguro acceder a los índices
    paradero_cod = context.args[0]
    nombre_alias = context.args[1]
    
    guardar_fav(update.effective_user.id, nombre_alias, paradero_cod)
    await update.message.reply_text(f"⭐ Guardado: *{nombre_alias}* ➔ `{paradero_cod.upper()}`", parse_mode='Markdown')

async def ver(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not update.message: return
    favs = obtener_favs(update.effective_user.id)
    if not favs:
        await update.message.reply_text("No tienes favoritos guardados.")
        return
    texto = "⭐ *Tus Favoritos:*\n" + "\n".join([f"• *{a}*: `{p}`" for a, p in favs.items()])
    await update.message.reply_text(texto, parse_mode='Markdown')

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data is not None and 'tarea_activa' in context.user_data:
        context.user_data['tarea_activa'].cancel()
        del context.user_data['tarea_activa']
        if update.message:
            await update.message.reply_text("💥 **¡BOOM!** Monitoreo detenido.", parse_mode='Markdown')
    elif update.message:
        await update.message.reply_text("No hay ningún monitoreo activo.")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await update.message.reply_text("🚌 **RedWatch Pro**\n\n`/p [alias]` - Empieza\n`/fav [código] [alias]` - Guarda\n`/stop` - Detona")

if __name__ == '__main__':
    if not TOKEN or not DB_URL:
        print("❌ Error de variables de entorno.")
    else:
        app = ApplicationBuilder().token(TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("p", monitor))
        app.add_handler(CommandHandler("fav", fav))
        app.add_handler(CommandHandler("ver", ver))
        app.add_handler(CommandHandler("stop", stop))
        app.run_polling()
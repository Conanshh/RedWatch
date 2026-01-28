import asyncio
import os
import logging
import psycopg2
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from main import obtener_tiempos
import threading
import uvicorn 

# Configuración de logs del sistema
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO
)

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
        logging.error(f"❌ Error DB Guardar: {e}")
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
        logging.error(f"❌ Error DB Obtener: {e}")
        return {}
    finally:
        if conn: conn.close()

# --- LÓGICA DE MONITOREO (EL MOTOR) ---

async def tarea_monitoreo(chat_id: int, user_id: int, paradero: str, context: ContextTypes.DEFAULT_TYPE):
    print(f"DEBUG: [Iniciando Bucle] Usuario: {user_id}, Paradero: {paradero}")
    try:
        es_primer_ciclo = True
        while True:
            # Feedback visual de "Escribiendo..." en Telegram
            await context.bot.send_chat_action(chat_id=chat_id, action="typing")
            
            # --- LÓGICA DE DETECCIÓN DE DESPERTAR ---
            task_api = asyncio.create_task(obtener_tiempos(paradero))
            print(f"DEBUG: [Scraping] Llamando a obtener_tiempos para {paradero}...")
            # Si es el primer mensaje, esperamos un poco y avisamos si se demora
            if es_primer_ciclo:
                done, pending = await asyncio.wait([task_api], timeout=25)
                if task_api in pending:
                    await context.bot.send_message(
                        chat_id=chat_id, 
                        text="💤 *El servidor está despertando...*\nEsto tomará 3-4 minutos, luego cada cambio llegará en menos de 1 minuto.",
                        parse_mode='Markdown'
                    )

            # Esperamos el resultado real (sin importar cuánto tarde)
            datos = await task_api 
            es_primer_ciclo = False # Ya despertó o ya pasó el primer intento
            
            print(f"DEBUG: [Resultado Scraping] {datos}")
            
            if datos is not None and isinstance(datos, dict) and 'notificacion' in datos:
                notificacion = datos.get('notificacion', 'Sin info.')
                msg = str(notificacion).replace("min", "*min*")
                
                # Verificación de seguridad antes de enviar
                await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode='Markdown')
            else:
                print(f"DEBUG: [Fallo] La API no devolvió un diccionario válido o 'notificacion' no existe.")
                await context.bot.send_message(chat_id=chat_id, text=f"⚠️ No hay buses para `{paradero}` ahora.")

            print("DEBUG: [Esperando] 20 segundos para el siguiente ciclo...")
            # Sleep fraccionado para permitir cancelación instantánea
            for _ in range(20): 
                await asyncio.sleep(1)
                
    except asyncio.CancelledError:
        print(f"DEBUG: [Bomba] Tarea cancelada correctamente para el usuario {user_id}")
        raise
    except Exception as e:
        print(f"DEBUG: [ERROR CRÍTICO] {e}")
        # Evitar que el bot muera por un error de red
        try:
            await context.bot.send_message(chat_id=chat_id, text="🚨 Error interno. Reintentando en breve...")
        except:
            pass
        await asyncio.sleep(10)

# --- COMANDOS ---

async def monitor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Blindaje de objetos base
    if not update.effective_user or not update.effective_chat or not update.message or context.user_data is None:
        return

    # Blindaje de argumentos
    if not context.args or len(context.args) < 1:
        await update.message.reply_text("❌ Uso: `/p [alias/código]`")
        return

    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    entrada = str(context.args[0]).lower().strip()

    # Cancelar tarea previa si el usuario ya estaba rastreando algo
    if 'tarea_activa' in context.user_data:
        print(f"DEBUG: Cancelando tarea anterior para el usuario {user_id}")
        context.user_data['tarea_activa'].cancel()

    # Buscar en favoritos o usar código directo
    favs = obtener_favs(user_id)
    paradero = favs.get(entrada, entrada).upper()
    
    await update.message.reply_text(f"🚀 **Monitoreando:** `{paradero}`\n_Deténlo con /stop_", parse_mode='Markdown')

    # Lanzar proceso asíncrono y guardarlo en memoria del bot
    task = asyncio.create_task(tarea_monitoreo(chat_id, user_id, paradero, context))
    context.user_data['tarea_activa'] = task

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data is not None and 'tarea_activa' in context.user_data:
        context.user_data['tarea_activa'].cancel()
        del context.user_data['tarea_activa']
        if update.message:
            await update.message.reply_text("💥 **¡BOOM!** Monitoreo detenido.")
    else:
        if update.message:
            await update.message.reply_text("No hay ningún monitoreo activo.")

async def fav(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not update.message or not context.args or len(context.args) < 2:
        if update.message:
            await update.message.reply_text("❌ Uso: `/fav [código] [nombre]`\nEj: `/fav PB820 casa`")
        return
    
    p_id = str(context.args[0]).upper()
    alias = str(context.args[1]).lower()
    
    guardar_fav(update.effective_user.id, alias, p_id)
    await update.message.reply_text(f"⭐ Guardado: *{alias}* ➔ `{p_id}`", parse_mode='Markdown')

async def ver(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not update.message: return
    favs = obtener_favs(update.effective_user.id)
    if not favs:
        await update.message.reply_text("No tienes favoritos guardados.")
        return
    texto = "⭐ *Tus Favoritos:*\n" + "\n".join([f"• *{a}*: `{p}`" for a, p in favs.items()])
    await update.message.reply_text(texto, parse_mode='Markdown')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await update.message.reply_text(
            "🚌 **RedWatch**\n\n"
            "`/p PB820` - Monitoreo directo\n"
            "`/fav PB820 casa` - Guardar favorito\n"
            "`/p casa` - Usar alias\n"
            "`/stop` - Detener todo\n\n"
            "⚠️ _Nota: Si es la primera consulta, el servidor puede tardar 3-4 min en despertar por estar alojado en una tier gratis._",
            parse_mode='Markdown'
        )

def run_api():
    # Esta función corre la API de FastAPI
    port = int(os.getenv("PORT", 10000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, log_level="info")

if __name__ == '__main__':
    print("DEBUG: Intentando iniciar el bot...")
    if not TOKEN or not DB_URL:
        print("❌ Error: Faltan variables de entorno (TELEGRAM_TOKEN o DATABASE_URL).")
    else:
        # 1. Lanzamos FastAPI en un hilo separado (daemon para que muera si el bot muere)
        api_thread = threading.Thread(target=run_api, daemon=True)
        api_thread.start()
        print("🚀 API levantada en hilo secundario...")

        app = ApplicationBuilder().token(TOKEN).build()
        
        # Handlers
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("p", monitor))
        app.add_handler(CommandHandler("fav", fav))
        app.add_handler(CommandHandler("ver", ver))
        app.add_handler(CommandHandler("stop", stop))
        
        print("🚀 BOT LISTO Y ESCUCHANDO...")
        app.run_polling()
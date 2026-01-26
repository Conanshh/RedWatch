import os
import re
import uvicorn
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from playwright.async_api import async_playwright
from dotenv import load_dotenv

load_dotenv()
app = FastAPI()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL, "http://localhost:3000"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/paradero/{codigo}")
async def obtener_tiempos(codigo: str):
    logger.info(f"🔍 [SCRAPER] Iniciando consulta para: {codigo.upper()}")
    
    # Inicializamos browser como None para evitar el error de "desvinculado"
    browser = None
    
    async with async_playwright() as p:
        try:
            logger.info("🚀 [SCRAPER] Lanzando Chromium...")
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
            )
            
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            
            url = f"https://www.red.cl/planifica-tu-viaje/cuando-llega/?codsimt={codigo.upper()}"
            logger.info(f"🌐 [SCRAPER] Navegando a: {url}")
            
            await page.goto(url, wait_until="networkidle", timeout=30000)
            
            logger.info("⏱️ [SCRAPER] Esperando selector .tabla-paradero...")
            try:
                await page.wait_for_selector(".tabla-paradero", timeout=15000)
            except Exception:
                logger.warning(f"⚠️ [SCRAPER] No hay tabla para {codigo}.")
                await browser.close()
                browser = None # Marcamos como cerrado
                return {"paradero": codigo.upper(), "notificacion": "No hay buses disponibles.", "servicios": []}

            filas = await page.query_selector_all(".tabla-paradero tbody tr")
            servicios = []

            for fila in filas:
                linea_el = await fila.query_selector("a.bus")
                tiempo_el = await fila.query_selector(".tiempo-llegada")
                
                if linea_el and tiempo_el:
                    linea = (await linea_el.inner_text()).strip()
                    raw_text = await tiempo_el.inner_text()
                    clean_text = raw_text.replace("Desvío planificado", "").strip()
                    
                    distancia = "99.9km"
                    tiempo = clean_text
                    
                    match_distancia = re.search(r"(\d+(\.\d+)?km)", clean_text)
                    if match_distancia:
                        distancia = match_distancia.group(1)
                    
                    match_tiempo = re.search(r"\((.*?)\)", clean_text)
                    if match_tiempo:
                        tiempo = match_tiempo.group(1)
                    elif "menos de" in clean_text.lower():
                        tiempo = "Llegando"

                    servicios.append({
                        "linea": linea,
                        "distancia": distancia,
                        "llegada": tiempo,
                        "alerta": "⚠️" if "Desvío" in raw_text else ""
                    })

            logger.info(f"✅ [SCRAPER] Éxito. Encontrados {len(servicios)} servicios.")
            
            def sort_key(s):
                try: return float(s['distancia'].replace('km', ''))
                except: return 999.0

            servicios_ordenados = sorted(servicios, key=sort_key)
            notif_parts = [f"🚌 {s['linea']}: {s['distancia']} ({s['llegada']}){s['alerta']}" for s in servicios_ordenados]
            mensaje = "\n".join(notif_parts)

            await browser.close()
            browser = None
            return {
                "paradero": codigo.upper(),
                "notificacion": mensaje if mensaje else "Sin buses ahora.",
                "servicios": servicios_ordenados
            }

        except Exception as e:
            logger.error(f"❌ [SCRAPER] Error crítico: {str(e)}")
            if browser: # Solo cerramos si realmente se llegó a crear
                await browser.close()
            return {"error": "Error de conexión", "detalle": str(e)}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
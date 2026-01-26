import os
import re
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from playwright.async_api import async_playwright
from dotenv import load_dotenv

# Carga variables desde .env en local, en Render se configuran en el panel
load_dotenv()

app = FastAPI()

# Leemos la URL de Vercel desde el entorno, si no existe usamos localhost
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        FRONTEND_URL,          # URL real de tu Vercel
        "http://localhost:3000" # Para pruebas locales
    ], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/paradero/{codigo}")
async def obtener_tiempos(codigo: str):
    print(f"\n--- CONSULTANDO PARADERO: {codigo.upper()} ---")
    async with async_playwright() as p:
        # Launch con argumentos para entornos Docker/Cloud (necesario en Render)
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox"]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        try:
            url = f"https://www.red.cl/planifica-tu-viaje/cuando-llega/?codsimt={codigo.upper()}"
            await page.goto(url, wait_until="networkidle", timeout=20000)
            await page.wait_for_selector(".tabla-paradero", timeout=15000)
            
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
                        tiempo = "Llegando ahora"

                    servicios.append({
                        "linea": linea,
                        "distancia": distancia,
                        "llegada": tiempo,
                        "alerta": "⚠️" if "Desvío" in raw_text else ""
                    })

            def sort_key(s):
                try:
                    return float(s['distancia'].replace('km', ''))
                except:
                    return 999.0

            servicios_ordenados = sorted(servicios, key=sort_key)
            notif_parts = [f"🚌 {s['linea']}: {s['distancia']} ({s['llegada']}){s['alerta']}" for s in servicios_ordenados]
            mensaje_reloj = "\n".join(notif_parts)

            await browser.close()
            return {
                "paradero": codigo.upper(),
                "notificacion": mensaje_reloj,
                "servicios": servicios_ordenados
            }

        except Exception as e:
            await browser.close()
            return {"error": "Fallo al capturar", "detalle": str(e)}

if __name__ == "__main__":
    # Render usa el puerto 10000 por defecto, pero es mejor leerlo del entorno
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
from fastapi import FastAPI
from playwright.async_api import async_playwright
import uvicorn
import re
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://tu-proyecto-frontend.vercel.app", # URL de Vercel
        "http://localhost:3000"                    # Para seguir probando local
    ], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/paradero/{codigo}")
async def obtener_tiempos(codigo: str):
    print(f"\n--- CONSULTANDO PARADERO: {codigo.upper()} ---")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        try:
            url = f"https://www.red.cl/planifica-tu-viaje/cuando-llega/?codsimt={codigo.upper()}"
            await page.goto(url, wait_until="networkidle")
            await page.wait_for_selector(".tabla-paradero", timeout=10000)
            
            filas = await page.query_selector_all(".tabla-paradero tbody tr")
            servicios = []

            for fila in filas:
                linea_el = await fila.query_selector("a.bus")
                tiempo_el = await fila.query_selector(".tiempo-llegada")
                
                if linea_el and tiempo_el:
                    linea = (await linea_el.inner_text()).strip()
                    # Limpiamos el texto de posibles avisos de desvío o iconos
                    raw_text = await tiempo_el.inner_text()
                    # Quitamos "Desvío planificado" si aparece en el texto capturado
                    clean_text = raw_text.replace("Desvío planificado", "").strip()
                    
                    distancia = "99.9km"
                    tiempo = clean_text
                    
                    # Usamos Regex para buscar el kilometraje (ej: 1.3km)
                    # Esto es mucho más seguro que el split()
                    match_distancia = re.search(r"(\d+(\.\d+)?km)", clean_text)
                    if match_distancia:
                        distancia = match_distancia.group(1)
                    
                    # Extraemos lo que está entre paréntesis para el tiempo
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

            # Ordenamos: primero las que tengan menor kilometraje numérico
            # Convertimos "2.3km" a 2.3 para poder comparar
            def sort_key(s):
                try:
                    return float(s['distancia'].replace('km', ''))
                except:
                    return 999.0

            servicios_ordenados = sorted(servicios, key=sort_key)
            
            # Formateamos el mensaje para el reloj
            notif_parts = []
            for s in servicios_ordenados:
                alerta_str = s['alerta']
                notif_parts.append(f"🚌 {s['linea']}: {s['distancia']} ({s['llegada']}){alerta_str}")
            
            mensaje_reloj = "\n".join(notif_parts)

            await browser.close()
            print(f"✅ Éxito: {len(servicios)} buses procesados.")
            return {
                "paradero": codigo.upper(),
                "notificacion": mensaje_reloj,
                "servicios": servicios_ordenados
            }

        except Exception as e:
            print(f"❌ Error: {str(e)}")
            await browser.close()
            return {"error": "Fallo al capturar", "detalle": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
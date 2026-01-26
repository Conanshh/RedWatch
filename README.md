# 🚌 RedWatch Pro 

Monitor de tiempos de llegada para buses Red (ex-Transantiago) en tiempo real. Este ecosistema integra una **PWA**, un **Bot de Telegram** y un **Scraper de alta precisión** para ofrecer información exacta cuando más la necesitas.

> **Bot de Telegram Oficial:** [@redwatch1bot](https://t.me/redwatch1bot)

---

## ✨ Características Principales

- **Notificaciones en Tiempo Real:** El bot de Telegram actualiza el estado de tu paradero cada 20 segundos automáticamente.
- **Persistencia con Neon:** Guarda tus paraderos más usados mediante alias (ej: `/p casa`) gracias a la integración con PostgreSQL.
- **Scraping de Alta Precisión:** Utiliza **Playwright** para extraer datos directamente desde la fuente oficial (Red.cl), garantizando veracidad incluso en buses con desvíos.
- **Modo PWA:** Interfaz web instalable en dispositivos Android e iOS para una experiencia de aplicación nativa.
- **Sistema de Monitoreo Inteligente:** Arquitectura asíncrona que permite iniciar, detener o cambiar de paradero sin bloqueos.

---

## 🛠️ Stack Tecnológico

### Backend & Bot
- **Lenguaje:** [Python 3.13+](https://www.python.org/)
- **Framework API:** [FastAPI](https://fastapi.tiangolo.com/) 
- **Librería del Bot:** [python-telegram-bot](https://python-telegram-bot.org/) (Asíncrona)
- **Motor de Navegación:** [Playwright](https://playwright.dev/python/) (Headless Chromium)
- **Base de Datos:** [PostgreSQL](https://www.postgresql.org/) (Hospedado en [Neon.tech](https://neon.tech/))

### Frontend
- **Framework:** [Astro](https://astro.build/) & [React.js](https://reactjs.org/)
- **PWA:** Service Workers API para caché y offline-ready.

---

## 🚀 Comandos del Bot de Telegram

Interactúa con **@redwatch1bot** usando los siguientes comandos:

- `/start` - Información general y bienvenida.
- `/p [código]` - Inicia el monitoreo en tiempo real de un paradero (Ej: `/p PB719`).
- `/p [alias]` - Monitorea un paradero guardado previamente (Ej: `/p casa`).
- `/fav [código] [alias]` - Guarda un paradero en tus favoritos con un nombre personalizado.
- `/ver` - Muestra tu lista de favoritos guardados.
- `/stop` - Detiene el monitoreo activo y libera recursos.

---

## 💻 Instalación y Desarrollo Local

1. **Clonar el repositorio:**
   ```bash
   git clone [https://github.com/tu-usuario/redwatch.git](https://github.com/tu-usuario/redwatch.git)
   cd redwatch
   ```
2. **Instalar dependencias:**
    ```bash
    cd red-backend
    pip install -r requirements.txt
    playwright install chromium
    ```
3. **Configurar variables de entorno**:

        TELEGRAM_TOKEN=tu_token_de_botfather
        DATABASE_URL=tu_url_de_neon_db
        PORT=8000
        PUBLIC_API_URL=http://localhost:8000

4. **Ejecutar**:

        python tbot.py & uvicorn main:app --reload

5.  **Configurar y ejecutar frontend:**

        cd ../red-frontend
        npm install
        npm run dev

## Despliegue
- Frontend: Desplegado en Vercel para máxima velocidad de entrega.

- Backend & Bot: Hospedado en Render mediante un servicio de Web Service que corre ambos procesos simultáneamente.

- Base de Datos: Instancia Serverless en Neon.tech.


---

## 👨‍💻 Autor

Desarrollado por **Ignacio Fuentes Ovalle**. 

Apasionado por crear soluciones tecnológicas que optimizan el día a día. Si tienes alguna duda, sugerencia o simplemente quieres conectar, puedes encontrarme en:

[![LinkedIn](https://img.shields.io/badge/LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/ignacio-fuentes-ovalle-980850396/)
[![GitHub](https://img.shields.io/badge/GitHub-100000?style=for-the-badge&logo=github&logoColor=white)](https://github.com/Conanshh)
---
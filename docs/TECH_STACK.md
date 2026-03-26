# 🛠️ Tech Stack - EasternTales Shelf

Key technologies used in the EasternTales Shelf application.

## ⚙️ Backend

### Core Technologies
*   ![Python](https://img.shields.io/badge/Python-3776AB?style=flat&logo=python&logoColor=white) 🐍 Primary backend language.
*   ![Flask](https://img.shields.io/badge/Flask-000000?style=flat&logo=flask&logoColor=white) 🌐 Main web framework.
*   ![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white) ⚡ Async tasks & `/sync` endpoint.

### Authentication & Authorization
* ![Flask-Login](https://img.shields.io/badge/Flask--Login-Session%20Management-blue)
*   🛡️ Custom Decorators (`admin_required`).
*   🔗 OAuth2 (AniList).

### Database & Data Access
* ![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-ORM-red) ![SQLite](https://img.shields.io/badge/SQLite-003B57?style=flat&logo=sqlite&logoColor=white)
*   ![MariaDB](https://img.shields.io/badge/MariaDB-003545?style=flat&logo=mariadb&logoColor=white) ![MySQL](https://img.shields.io/badge/MySQL-4479A1?style=flat&logo=mysql&logoColor=white) 🗄️ Primary engines.
*   🔌 `pymysql` driver.
*   ✍️ Raw SQL helpers.

### API Communication & Integration
*   ![GraphQL](https://img.shields.io/badge/GraphQL-E10098?style=flat&logo=graphql&logoColor=white) 📈 Consuming AniList API.
*   📡 HTTP Clients: `requests`, `httpx`, `aiohttp`.

### Asynchronous Operations & Real-time
* ![Flask-SocketIO](https://img.shields.io/badge/Flask--SocketIO-Real--Time-black)
*   ⏳ Async: `threading`, `asyncio`, `schedule`.

### Web Scraping
![Beautiful Soup 4](https://img.shields.io/badge/Beautiful%20Soup%204-HTML%20Parsing-orange)  ![Scrapy](https://img.shields.io/badge/Scrapy-Web%20Crawling-green)

### AI/ML Integration
![Groq](https://img.shields.io/badge/Groq-AI%2FML-blueviolet)  ![Pinecone](https://img.shields.io/badge/Pinecone-Vector%20DB-blue) ![VoyageAI](https://img.shields.io/badge/VoyageAI-Embeddings-brightgreen) ![Transformers](https://img.shields.io/badge/Transformers-NLP-yellow)   ![NumPy](https://img.shields.io/badge/NumPy-4D77CF?style=flat&logo=numpy&logoColor=white)

### Utilities & Services
![Doppler](https://img.shields.io/badge/Doppler-Secrets-black?style=flat&logo=doppler&logoColor=white)  ![Pillow](https://img.shields.io/badge/Pillow-Image%20Processing-lightblue)  ![Gunicorn](https://img.shields.io/badge/Gunicorn-499848?style=flat&logo=gunicorn&logoColor=white)

## ✨ Frontend

### Markup & Templating
* ![Jinja](https://img.shields.io/badge/Jinja-B41717?style=flat&logo=jinja&logoColor=white)
*   ![HTML5](https://img.shields.io/badge/HTML5-E34F26?style=flat&logo=html5&logoColor=white) 📄 Structure.
*   📦 Static assets (`app/static`).

### Styling & UI Frameworks
* ![Element UI](https://img.shields.io/badge/Element%20UI-Component%20Library-409EFF)
*   ![CSS3](https://img.shields.io/badge/CSS3-1572B6?style=flat&logo=css3&logoColor=white) 💅 Custom styling.
*   ![Bootstrap](https://img.shields.io/badge/Bootstrap-7952B3?style=flat&logo=bootstrap&logoColor=white) 🅱️ UI components/grid.

### JavaScript & Interactivity
* ![GSAP](https://img.shields.io/badge/GSAP-Animation-88CE02?logo=greensock) ![JavaScript](https://img.shields.io/badge/JavaScript-ES6%20Modules-F7DF1E?logo=javascript)
*   ![jQuery](https://img.shields.io/badge/jQuery-0769AD?style=flat&logo=jquery&logoColor=white) 💲 DOM/AJAX.
*   ![Vue.js](https://img.shields.io/badge/Vue.js-4FC08D?style=flat&logo=vuedotjs&logoColor=white) 💚 Specific components.
*   📡 Fetch API.

### Icons & Fonts
*   ![Font Awesome](https://img.shields.io/badge/Font%20Awesome-528DD7?style=flat&logo=fontawesome&logoColor=white) 🎭 Icons.

## 🚀 DevOps & Infrastructure

### Configuration & Secrets
* ![Doppler](https://img.shields.io/badge/Doppler-Secrets-black?style=flat&logo=doppler&logoColor=white)

### Development Workflow
* ![pip](https://img.shields.io/badge/pip-Package%20Manager-3B74A7) ![Tkinter](https://img.shields.io/badge/Tkinter-GUI-blue)
*   ![Git](https://img.shields.io/badge/Git-F05032?style=flat&logo=git&logoColor=white) 🌿 Version control.
*   🛠️ CLI Helpers.

## 🌐 External APIs & Services

### Content & Data Sources
*   ![AniList](https://img.shields.io/badge/AniList-API-2DB0F3?logo=anilist) 📖 Primary data (OAuth2/GraphQL).
*   📰 MangaUpdates (API/Scraping).
*   📚 Bato.to (Scraping).

### AI Services
*   ![Groq](https://img.shields.io/badge/Groq-AI%2FML-blueviolet) 💡 LLM API.

### Internal Services
*   ![FastAPI](https://img.shields.io/badge/FastAPI-Internal%20Sync-009688?logo=fastapi) �� `/sync` endpoint.
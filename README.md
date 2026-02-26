🩺 AI Health Detector (Aika)
AI Health Detector — это веб-приложение на Flask, которое использует искусственный интеллект для персонального анализа здоровья и симптомов. Система поддерживает работу с несколькими ИИ-провайдерами, включая локальный запуск через Ollama.

🚀 Key Features
Multi-Model AI Support: Интеграция с OpenAI (GPT-4o-mini), HuggingFace и Ollama (локальные LLM).

Smart Dashboard: Генерация персональных советов на основе мед-профиля пользователя (ИМТ, хронические заболевания, аллергии).

Symptom Tracker: Чат-интерфейс для обсуждения симптомов с сохранением истории.

Photo Analysis: Загрузка и анализ кожных снимков (с поддержкой конвертации HEIC в JPG).

Privacy First: Возможность работы полностью офлайн при использовании Ollama.

🛠 Tech Stack
Backend: Python 3.x, Flask

Database: SQLAlchemy (SQLite)

AI/ML: OpenAI API, HuggingFace Inference API, Ollama (Mistral/SmolLM)

Auth: Flask-Login (с хешированием паролей через PBKDF2)

Frontend: Jinja2 Templates, CSS3

📦 Installation & Setup
Clone the repository:

Bash
git clone https://github.com/yourusername/ai-health-detector.git
cd ai-health-detector
Install dependencies:

Bash
pip install -r requirements.txt
Configure Environment Variables:
Create a .env file:

Фрагмент кода
AI_PROVIDER=ollama  # openai | huggingface | ollama
OPENAI_API_KEY=your_key
HF_API_KEY=your_key
OLLAMA_MODEL=mistral
SECRET_KEY=your_random_secret
Run the application:

Bash
python app.py
📋 Database Models
User: Хранит медицинские данные (возраст, вес, привычки).

Symptom: Логирует жалобы и категории ответов ИИ.

Photo: Хранит пути к изображениям и результаты анализа.

Tip: Архив сгенерированных советов.

⚠️ Disclaimer
This application is a demo project for educational purposes. It provides AI-generated suggestions, not medical diagnoses. Always consult a professional doctor.

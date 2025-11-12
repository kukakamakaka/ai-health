import os
import json
import random
import requests
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
load_dotenv()
from openai import OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

from flask_login import (
    LoginManager, login_user, logout_user, login_required, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash

# ВАЖНО: из models импортируем User (должен быть описан в models.py)
from models import db, User, Symptom, Photo, Tip

# ------------------ ENV ------------------

AI_PROVIDER   = os.getenv("AI_PROVIDER", "openai")               # openai | huggingface | ollama
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
HF_API_KEY     = os.getenv("HF_API_KEY")
HF_MODEL       = os.getenv("HF_MODEL", "HuggingFaceTB/SmolLM3-3B")
OLLAMA_MODEL   = os.getenv("OLLAMA_MODEL", "mistral")

SECRET_KEY     = os.getenv("SECRET_KEY", "change-me-in-.env")   # для Flask-Login

# ------------------ Flask app ------------------
app = Flask(__name__)
app.secret_key = SECRET_KEY


app.jinja_env.globals.update(now=datetime.now)


# Готовим папки: instance (SQLite) и uploads (фото)
BASE_DIR      = os.path.dirname(__file__)
INSTANCE_DIR  = os.path.join(BASE_DIR, "instance")
UPLOAD_DIR    = os.path.join(BASE_DIR, "static", "uploads")
os.makedirs(INSTANCE_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

# База данных
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///{}".format(
    os.path.join(os.path.abspath(os.path.dirname(__file__)), "instance", "health.db")
)

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["UPLOAD_FOLDER"] = UPLOAD_DIR

db.init_app(app)
with app.app_context():
    db.create_all()

# ------------------ Login Manager ------------------
login_manager = LoginManager()
login_manager.login_view = "login"  # редирект сюда если не авторизован
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id: str):
    return User.query.get(int(user_id))

# ------------------ AI Core ------------------
def ask_aika(prompt: str) -> str:
    """
    Универсальный вызов ИИ: OpenAI / HuggingFace / Ollama
    Всегда отвечаем ТОЛЬКО на английском.
    """
    try:
        # ---- OpenAI ----
        if AI_PROVIDER == "openai" and OPENAI_API_KEY:
            completion = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are Aika — a friendly health assistant. "
                            "Always reply ONLY in English, never in any other language. "
                            "Be concise and kind. End every response with: 'This is not a diagnosis.'"
                        )
                    },
                    {"role": "user", "content": prompt}
                ]
            )
            return completion.choices[0].message.content.strip()

        # ---- HuggingFace ----
        elif AI_PROVIDER == "huggingface" and HF_API_KEY:
            # многие модели HF не имеют Chat API — используем text generation endpoint
            resp = requests.post(
                f"https://api-inference.huggingface.co/models/{HF_MODEL}",
                headers={"Authorization": f"Bearer {HF_API_KEY}"},
                json={
                    "inputs": f"Reply only in English. {prompt}",
                    "parameters": {"max_new_tokens": 180}
                },
                timeout=90
            )
            if resp.status_code == 200:
                try:
                    data = resp.json()
                    # Формат HF бывает разный
                    if isinstance(data, list) and data and "generated_text" in data[0]:
                        return data[0]["generated_text"].strip()
                    if isinstance(data, dict) and "generated_text" in data:
                        return data["generated_text"].strip()
                    # Если пришёл другой формат — возвращаем строку как есть
                    return str(data)
                except Exception as e:
                    print("HF JSON PARSE ERROR:", e)
                    return "⚠️ Error parsing HuggingFace response. This is not a diagnosis."
            else:
                return f"⚠️ HuggingFace API error {resp.status_code}: {resp.text}"

        # ---- Ollama (локально) ----
        elif AI_PROVIDER == "ollama":
            # Принудительно просим английский
            local_prompt = f"Reply only in English. {prompt}"
            resp = requests.post(
                "http://127.0.0.1:11434/api/generate",
                json={"model": OLLAMA_MODEL, "prompt": local_prompt},
                timeout=90,
                stream=True  # читаем стримом
            )

            if resp.status_code == 200:
                response_text = ""
                for line in resp.iter_lines():
                    if not line:
                        continue
                    try:
                        obj = json.loads(line.decode("utf-8"))
                        chunk = obj.get("response", "")
                        if chunk:
                            response_text += chunk
                    except Exception as e:
                        print("Ollama stream JSON parse error:", e)
                        continue
                return response_text.strip() or "⚠️ Empty response from Ollama. This is not a diagnosis."
            else:
                return f"⚠️ Ollama error {resp.status_code}: {resp.text}"

        # ---- Нет провайдера / ключа ----
        else:
            return random.choice([
                "Try to rest and drink some water 💧 (This is not a diagnosis.)",
                "If you feel worse, contact a doctor ⚕️ (This is not a diagnosis.)",
                "Monitor your symptoms 🙏 (This is not a diagnosis.)"
            ])

    except Exception as e:
        print("AI ERROR:", e)
        return random.choice([
            "Try to rest and drink some water 💧 (This is not a diagnosis.)",
            "If you feel worse, contact a doctor ⚕️ (This is not a diagnosis.)",
            "Monitor your symptoms 🙏 (This is not a diagnosis.)"
        ])

# ------------------ Routes: Public ------------------
@app.route("/")
def index():
    # Гостевая «обложка» без аккаунта
    return render_template("index.html")

# ------------------ Auth ------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        gender = request.form.get("gender")
        age = request.form.get("age")
        height = request.form.get("height")
        weight = request.form.get("weight")
        chronic = request.form.get("chronic_conditions")
        allergies = request.form.get("allergies")
        medications = request.form.get("medications")

        # ✅ Проверка: есть ли уже пользователь с таким email
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            error = "⚠️ This email is already registered. Please log in instead."
            return render_template("register.html", error=error)

        # 🔒 Создание нового пользователя
        hashed_pw = generate_password_hash(password, method="pbkdf2:sha256", salt_length=8)
        new_user = User(
            username=username,
            email=email,
            password=hashed_pw,
            gender=gender,
            age=int(age) if age else None,
            height=float(height) if height else None,
            weight=float(weight) if weight else None,
            health_conditions=chronic,
            allergies=allergies,
            medications=medications
        )

        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for("login"))
    return render_template("register.html")


from flask import request

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            next_page = request.args.get("next")
            return redirect(next_page or url_for("index"))  # если нет next → на index
        return render_template("login.html", error="Invalid credentials.")
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))

# ------------------ Dashboard (Personalized) ------------------
@app.route("/dashboard")
@login_required
def dashboard():
    profile = current_user

    # 🩺 Собираем описание профиля для AI-совета
    profile_info = (
        f"The user is {profile.age or 'unknown'} years old, "
        f"gender {profile.gender or 'unspecified'}, "
        f"height {profile.height or 'unknown'} cm, "
        f"weight {profile.weight or 'unknown'} kg. "
        f"Health conditions: {profile.health_conditions or 'none'}. "
        f"Allergies: {profile.allergies or 'none'}. "
        f"Medications: {profile.medications or 'none'}. "
        f"Sleep hours: {profile.sleep_hours or 'unknown'} per night. "
        f"Activity level: {profile.activity_level or 'not specified'}. "
        f"Diet type: {profile.diet_type or 'not specified'}. "
        f"Smoking: {'yes' if profile.smoking else 'no'}, "
        f"Alcohol: {'yes' if profile.alcohol else 'no'}."
    )

    # 🧠 Генерация персонального совета на основе данных
    advice = ask_aika(
        f"{profile_info} Based on this health profile, give one short, friendly, personalized health advice. "
        f"Keep it under 50 words and make it motivational. This is not a diagnosis."
    )

    # ⚙️ Отправляем всё в шаблон dashboard.html
    return render_template("base.html", user=profile, advice=advice)

# ---------- Edit Profile ----------
@app.route("/edit_profile", methods=["GET", "POST"])
@login_required
def edit_profile():
    user = current_user

    if request.method == "POST":
        user.username = request.form.get("username", user.username)
        user.age = request.form.get("age", user.age)
        user.gender = request.form.get("gender", user.gender)
        user.height = request.form.get("height", user.height)
        user.weight = request.form.get("weight", user.weight)
        user.health_conditions = request.form.get("health_conditions", user.health_conditions)
        user.allergies = request.form.get("allergies", user.allergies)
        user.medications = request.form.get("medications", user.medications)
        user.sleep_hours = request.form.get("sleep_hours", user.sleep_hours)
        user.activity_level = request.form.get("activity_level", user.activity_level)
        user.diet_type = request.form.get("diet_type", user.diet_type)
        user.smoking = bool(request.form.get("smoking"))
        user.alcohol = bool(request.form.get("alcohol"))

        db.session.commit()
        return redirect(url_for("dashboard"))

    return render_template("edit_profile.html", user=user)

# ---------- Account Settings ----------
@app.route("/account")
@login_required
def account():
    user = current_user
    return render_template("account.html", user=user)


# ---------- Delete Account ----------
@app.route("/delete_account", methods=["POST"])
@login_required
def delete_account():
    user = current_user

    # Удаляем все связанные записи
    Symptom.query.delete()
    Photo.query.delete()
    Tip.query.delete()

    db.session.delete(user)
    db.session.commit()

    logout_user()
    return redirect(url_for("index"))


# ------------------ Symptom Chat (AI Chat Interface) ------------------
@app.route("/symptoms", methods=["GET", "POST"])
@login_required
def symptoms():
    from datetime import datetime

    if request.method == "POST":
        user_input = request.form.get("symptom", "").strip()
        if not user_input:
            return redirect(url_for("symptoms"))

        # Ask AI
        ai_response = ask_aika(
            f"The user says: '{user_input}'. Give a short English response (1–2 sentences) with care and clarity. This is not a diagnosis."
        )

        # Save to DB
        new_symptom = Symptom(text=user_input, category=ai_response)
        db.session.add(new_symptom)
        db.session.commit()

        return redirect(url_for("symptoms"))

    # Load chat history
    symptoms = Symptom.query.order_by(Symptom.created_at.asc()).all()
    for s in symptoms:
        s.time = s.created_at.strftime("%I:%M %p")
    return render_template("symptoms.html", symptoms=symptoms)


# ------------------ Photo (protected) ------------------
@app.route("/photo", methods=["GET", "POST"])
@login_required
def photo():

    result = None

    if request.method == "POST":
        file = request.files.get("photo")
        print("📥 Incoming request method:", request.method)
        file = request.files.get("photo")
        print("📸 File object:", file)
        if file:
            print("📁 Filename:", file.filename)

        if file and file.filename:
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(filepath)

            import PIL
            from PIL import Image

            # если файл HEIC — конвертируем в JPG
            if filename.lower().endswith(".heic"):
                try:
                    from pillow_heif import register_heif_opener
                    register_heif_opener()

                    heic_image = Image.open(filepath)
                    new_filename = filename.rsplit(".", 1)[0] + ".jpg"
                    new_path = os.path.join(app.config["UPLOAD_FOLDER"], new_filename)
                    heic_image.save(new_path, format="JPEG")
                    os.remove(filepath)  # удаляем оригинал
                    filename = new_filename
                    filepath = new_path
                    print("✅ Converted HEIC → JPG:", filepath)
                except Exception as e:
                    print("⚠️ HEIC conversion failed:", e)

            # AI анализ
            ai_result = ask_aika(
                "The user uploaded a skin photo. "
                "Give a gentle English health suggestion (not a diagnosis)."
            )

            new_photo = Photo(filename=filename, result=ai_result)
            db.session.add(new_photo)
            db.session.commit()

            # 👇 добавь это
            result = {
                "filename": filename,
                "analysis": ai_result,
                "url": url_for("static", filename=f"uploads/{filename}")
            }
    return render_template("photo.html", result=result)

# ------------------ Tips (protected) ------------------
@app.route("/tips", methods=["GET", "POST"])
@login_required
def tips():
    if request.method == "POST":
        text = ask_aika("Give one short English tip about nutrition, sleep, or physical activity. This is not a diagnosis.")
        new_tip = Tip(text=text)
        db.session.add(new_tip)
        db.session.commit()
        return redirect(url_for("history"))

    return render_template("tips.html")

# ------------------ History (protected or public?) ------------------
# Если хочешь закрыть историю — оставь @login_required.
@app.route("/history")
@login_required
def history():
    symptoms = Symptom.query.order_by(Symptom.created_at.desc()).all()
    photos   = Photo.query.order_by(Photo.created_at.desc()).all()
    tips     = Tip.query.order_by(Tip.created_at.desc()).all()
    return render_template("history.html", symptoms=symptoms, photos=photos, tips=tips)


@app.route('/about')
def about():
    return render_template('about.html')

# ------------------ Run ------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))

    print("🧠 Flask started with:")
    print("AI_PROVIDER =", os.getenv("AI_PROVIDER"))
    print("OPENAI_API_KEY =", (os.getenv("OPENAI_API_KEY")[:10] + "...") if os.getenv("OPENAI_API_KEY") else None)

    app.run(host="0.0.0.0", port=port)


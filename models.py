from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

# -------------------------------
#  Пользователь с медпрофилем
# -------------------------------
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)

    # --- Основная информация ---
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # --- Медицинские данные ---
    age = db.Column(db.Integer, nullable=True)
    gender = db.Column(db.String(10), nullable=True)  # male / female / other
    height = db.Column(db.Float, nullable=True)
    weight = db.Column(db.Float, nullable=True)
    health_conditions = db.Column(db.Text, nullable=True)  # e.g. diabetes, asthma
    allergies = db.Column(db.Text, nullable=True)          # e.g. penicillin
    medications = db.Column(db.Text, nullable=True)        # e.g. metformin, ibuprofen

    # --- Лайфстайл данные ---
    sleep_hours = db.Column(db.Float, nullable=True)       # среднее кол-во часов сна
    activity_level = db.Column(db.String(20), nullable=True)  # low / moderate / high
    diet_type = db.Column(db.String(50), nullable=True)    # e.g. balanced, vegetarian
    smoking = db.Column(db.Boolean, default=False)
    alcohol = db.Column(db.Boolean, default=False)

    # Связи
    symptoms = db.relationship("Symptom", backref="user", lazy=True)
    photos = db.relationship("Photo", backref="user", lazy=True)
    tips = db.relationship("Tip", backref="user", lazy=True)

    def __repr__(self):
        return f"<User {self.username}>"


# -------------------------------
#  Симптомы
# -------------------------------
class Symptom(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    text = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Symptom {self.text[:20]}>"


# -------------------------------
#  Фото (например, кожные снимки)
# -------------------------------
class Photo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    filename = db.Column(db.String(255), nullable=False)
    result = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Photo {self.filename}>"


# -------------------------------
#  Советы (от AI)
# -------------------------------
class Tip(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Tip {self.text[:30]}>"



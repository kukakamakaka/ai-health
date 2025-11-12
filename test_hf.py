import os
import requests
from dotenv import load_dotenv

load_dotenv()

HF_API_KEY = os.getenv("HF_API_KEY")
HF_MODEL = os.getenv("HF_MODEL", "mistralai/Mistral-7B-Instruct-v0.3")

print("Пробую модель:", HF_MODEL)

resp = requests.post(
    f"https://api-inference.huggingface.co/models/{HF_MODEL}",
    headers={"Authorization": f"Bearer {HF_API_KEY}"},
    json={"inputs": "У меня болит голова, что делать?"}
)

print("Status:", resp.status_code)
print("Response:", resp.text[:500])

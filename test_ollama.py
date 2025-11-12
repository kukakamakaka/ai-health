import requests

prompt = "У меня болит зуб. Дай совет по здоровью (не диагноз)."

resp = requests.post(
    "http://localhost:11434/api/generate",
    json={"model": "mistral", "prompt": prompt}
)

print("Status:", resp.status_code)
print("Raw:", resp.text)

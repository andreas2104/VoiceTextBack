import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("keyUrl"))

response = client.chat.completions.create(
    model="gpt-5-mini",  # choisi un ID de modèle présent dans ta liste
    messages=[
        {"role": "system", "content": "Tu es un assistant utile."},
        {"role": "user", "content": "Bonjour !"}
    ]
)

print(response.choices[0].message["content"])

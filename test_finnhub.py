import os
from dotenv import load_dotenv
import requests

load_dotenv()

api_key = os.getenv("FINNHUB_API_KEY")

print("API Key:", api_key[:8] + "...")

response = requests.get(
    "https://finnhub.io/api/v1/news",
    params={
        "category": "general",
        "token": api_key,
    },
)

print("Status:", response.status_code)

data = response.json()

print("Antall artikler:", len(data))

if data:
    print("\nFørste artikkel:")
    print(data[0]["headline"])
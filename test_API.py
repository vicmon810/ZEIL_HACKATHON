

from google import genai

client = genai.Client()  # reads GEMINI_API_KEY
response = client.models.generate_content(
    model="gemini-flash-latest",
    contents="Give me three hackathon ideas about hiring.",
)
print(response.text)
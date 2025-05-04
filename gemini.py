from google import genai
import os


GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
BOT_TOKEN = os.getenv('BOT_TOKEN')


client = genai.Client(api_key=GEMINI_API_KEY)
basic_prompt= "I am feeling lucky today,tell me something good"


async def getResponseFromGemini(prompt=basic_prompt):
    
    response = await client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt,
    )
    return response.text


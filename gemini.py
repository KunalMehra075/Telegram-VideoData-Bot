from google import genai
import os
import logging

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
BOT_TOKEN = os.getenv('BOT_TOKEN')


client = genai.Client(api_key=GEMINI_API_KEY)
basic_prompt= "I am feeling lucky today,tell me something good"


def getResponseFromGemini(prompt=basic_prompt):
    try:
        response = client.models.generate_content(model="gemini-2.0-flash",contents=prompt)
        logger.info("Response generated successfully from Gemini")
        return response.text
    except Exception as e:
        logger.error(e)
        return None

     



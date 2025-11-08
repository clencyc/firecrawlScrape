import httpx
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

async def test_gemini_http():
    api_key = os.getenv("GEMINI_API_KEY")
    model = "gemini-2.5-flash"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}",
                json={
                    "contents": [{"parts": [{"text": "What is 2+2? Give a brief answer."}]}],
                    "generationConfig": {
                        "temperature": 0.3,
                        "maxOutputTokens": 100
                    }
                },
                timeout=30.0
            )
            
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                text = result["candidates"][0]["content"]["parts"][0]["text"]
                print(f"Gemini Response: {text}")
            else:
                print(f"Error Response: {response.text}")
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_gemini_http())
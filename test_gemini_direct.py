import json
import urllib.request
import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from django.conf import settings as django_settings

def test_gemini():
    api_key = django_settings.GEMINI_API_KEY.strip()
    print(f"DEBUG: Using Gemini API Key: {api_key[:10]}...")
    
    api_url = f"https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateContent?key={api_key}"
    
    payload = {
        "contents": [{
            "parts": [{"text": "Say hello!"}]
        }]
    }
    
    try:
        req = urllib.request.Request(
            api_url,
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )

        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode('utf-8'))
            print("SUCCESS!")
            print(f"Response: {result['candidates'][0]['content']['parts'][0]['text']}")
    except Exception as e:
        print(f"FAILED: {e}")
        if hasattr(e, 'read'):
             print(f"Response body: {e.read().decode('utf-8')}")

if __name__ == "__main__":
    test_gemini()

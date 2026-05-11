import json
import urllib.request
import os
import django
from decimal import Decimal

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from django.conf import settings as django_settings

def test_deepseek():
    api_key = django_settings.DEEPSEEK_API_KEY.strip()
    print(f"DEBUG: Using API Key: {api_key[:5]}...")
    
    api_url = "https://api.deepseek.com/chat/completions"
    
    prompt = "Say hello!"
    
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ],
        "stream": False
    }
    
    try:
        req = urllib.request.Request(
            api_url,
            data=json.dumps(payload).encode('utf-8'),
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {api_key}'
            }
        )

        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode('utf-8'))
            print("SUCCESS!")
            print(f"Response: {result['choices'][0]['message']['content']}")
    except Exception as e:
        print(f"FAILED: {e}")
        if hasattr(e, 'read'):
             print(f"Response body: {e.read().decode('utf-8')}")

if __name__ == "__main__":
    test_deepseek()

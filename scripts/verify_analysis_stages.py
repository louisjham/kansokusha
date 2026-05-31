import sys
import os
sys.path.append(os.getcwd())

from app import create_app
from app.services.openai_compatible_service import OpenAICompatibleService

app = create_app()

def test_streaming():
    with app.app_context():
        print("--- Testing OpenAICompatibleService (OpenRouter) Streaming ---")
        try:
             service = OpenAICompatibleService('openrouter')
             if not service.client:
                 print("OpenRouter not configured, skipping.")
                 return

             posts = [{'text': 'I hate the government!', 'platform': 'twitter', 'created_at': '2023-01-01'}]
             info = {'full_name': 'Test Subject', 'position': 'Tester'}

             gen = service.analyze_comprehensive(posts, info)
             for type, msg in gen:
                if type == 'result':
                     print(f"[{type}] Keys: {list(msg.keys())}")
                     print(f"Risk Score: {msg.get('risk_score')}")
                else:
                    print(f"[{type}] {msg}")
        except Exception as e:
             print(f"OpenRouter Test Failed: {e}")

if __name__ == "__main__":
    test_streaming()

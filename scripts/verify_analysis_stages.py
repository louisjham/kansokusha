import sys
import os
sys.path.append(os.getcwd())

from app import create_app
from app.services.gemini_service import GeminiService
from app.services.openai_compatible_service import OpenAICompatibleService

app = create_app()

def test_streaming():
    with app.app_context():
        print("--- Testing GeminiService Streaming ---")
        try:
            service = GeminiService()
            
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
            print(f"Gemini Test Failed: {e}")
            
        print("\n--- Testing OpenAICompatibleService (Z.AI) Streaming ---")
        try:
             service_zai = OpenAICompatibleService('z_ai')
             # Check if configured
             if not service_zai.client:
                 print("Z.AI not configured, skipping.")
                 return

             gen = service_zai.analyze_comprehensive(posts, info)
             for type, msg in gen:
                if type == 'result':
                     print(f"[{type}] Keys: {list(msg.keys())}")
                     print(f"Risk Score: {msg.get('risk_score')}")
                else:
                    print(f"[{type}] {msg}")
        except Exception as e:
             print(f"Z.AI Test Failed: {e}")

if __name__ == "__main__":
    test_streaming()

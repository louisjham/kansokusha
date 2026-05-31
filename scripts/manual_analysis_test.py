
import logging
import json
import os
from app import create_app, db
from app.models import AnalysisResult, Employee
from app.services.openai_compatible_service import OpenAICompatibleService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_test():
    app = create_app()
    with app.app_context():
        print("--- Starting Manual Analysis Test ---")
        
        # 1. Setup Dummy Data
        posts = [
            {"content": "I absolutely hate people who disagree with me. They should be removed.", "created_at": "2023-10-01T10:00:00Z", "url": "http://twitter.com/1"},
            {"content": "The government is hiding the truth about aliens and chips in vaccines.", "created_at": "2023-10-02T11:00:00Z", "url": "http://twitter.com/2"},
            {"content": "I feel worthless and I don't know if I can go on.", "created_at": "2023-10-03T12:00:00Z", "url": "http://twitter.com/3"},
            {"content": "Just had a great coffee at the new place downtown!", "created_at": "2023-10-04T09:00:00Z", "url": "http://twitter.com/4"}
        ]
        
        employee_info = {
            'employee_id': 'TEST-001',
            'full_name': 'Test Subject Alpha',
            'department': 'Security',
            'position': 'Analyst'
        }
        
        # 2. Select Provider
        print("Using Provider: openrouter")
        service = OpenAICompatibleService('openrouter')

        # 3. Run Analysis
        try:
            print("Sending request to LLM (this may take a few seconds)...")
            result = service.analyze_social_media_posts(posts, employee_info)
            
            print("\n--- Analysis Complete ---")
            print(f"Risk Score: {result.get('risk_score')}")
            print("\n--- Summary ---")
            print(result.get('summary'))
            
            print("\n--- Behavioral Insights ---")
            print(result.get('behavioral_insights'))
            
            print("\n--- Red Flags ---")
            print(json.dumps(result.get('red_flags'), indent=2))

            # Optional: Save to DB to verify model constraints
            # analysis = AnalysisResult(employee_id=1, ...) # skipped for now, focusing on service output
            
        except Exception as e:
            logger.exception("Analysis failed during test.")
            print(f"Error: {e}")

if __name__ == "__main__":
    run_test()

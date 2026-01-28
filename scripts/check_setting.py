
from app import create_app
from app.models import get_setting

app = create_app()
with app.app_context():
    print(f"ANALYSIS_PROVIDER: {get_setting('ANALYSIS_PROVIDER')}")
    print(f"ZAI_API_KEY Configured: {'Yes' if app.config.get('ZAI_API_KEY') else 'No'}")
    print(f"GEMINI_API_KEY Configured: {'Yes' if app.config.get('GOOGLE_API_KEY') else 'No'}")

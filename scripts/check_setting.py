
from app import create_app
from app.models import get_setting

app = create_app()
with app.app_context():
    print(f"ANALYSIS_PROVIDER: {get_setting('ANALYSIS_PROVIDER')}")
    print(f"OPENROUTER_API_KEY Configured: {'Yes' if get_setting('OPENROUTER_API_KEY') or app.config.get('OPENROUTER_API_KEY') else 'No'}")

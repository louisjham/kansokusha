
from app import create_app
from app.models import set_setting

app = create_app()
with app.app_context():
    print("Setting ANALYSIS_PROVIDER to 'z_ai'")
    set_setting('ANALYSIS_PROVIDER', 'z_ai')
    print("Done")

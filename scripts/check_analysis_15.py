
from app import create_app, db
from app.models import AnalysisResult

app = create_app()
with app.app_context():
    a = AnalysisResult.query.get(15)
    if a:
        print(f"Analysis {a.id}:")
        print(f"Risk Score: {a.risk_score}")
        print(f"Red Flags: {a.red_flags}")
        print(f"Raw Data (start): {str(a.raw_data)[:100]}")
    else:
        print("Analysis 15 not found")

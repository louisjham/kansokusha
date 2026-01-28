
from app import create_app, db
from app.models import AnalysisResult

app = create_app()
with app.app_context():
    # Fetch the latest analysis result (likely ID 15 or higher)
    a = AnalysisResult.query.order_by(AnalysisResult.id.desc()).first()
    if a:
        print(f"Analysis {a.id}:")
        print(f"Risk Score: {a.risk_score}")
        print(f"Red Flags: {a.get_red_flags()}")
        
        # Check raw_data content
        if a.raw_data:
            print(f"Raw Data Type: {type(a.raw_data)}")
            if isinstance(a.raw_data, str):
                 print(f"Raw Data (Tail 200 chars): ...{a.raw_data[-200:]}")
            else:
                 print("Raw Data is valid JSON object.")
        else:
            print("Raw Data is None/Empty")

    else:
        print("No analysis found")

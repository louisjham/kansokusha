
from app import create_app, db
from app.models import User

def ensure_admin():
    app = create_app()
    with app.app_context():
        username = "admin"
        email = "admin@example.com"
        password = "admin"
        
        user = User.query.filter_by(username=username).first()
        if not user:
            print(f"Creating admin user: {username}")
            user = User(username=username, email=email, role="system_admin", is_active=True)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            print("Admin user created successfully.")
        else:
            print("Admin user already exists. Updating password to 'admin'.")
            user.set_password(password)
            db.session.commit()
            print("Admin password updated.")

if __name__ == "__main__":
    ensure_admin()

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from config import config
import os
from flask_wtf.csrf import CSRFProtect, CSRFError

from flask_migrate import Migrate

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()

def configure_logging(app):
    from pythonjsonlogger import jsonlogger
    import logging.handlers

    log_handler = logging.handlers.RotatingFileHandler(
        'crystallens.log', maxBytes=10000000, backupCount=5
    )
    formatter = jsonlogger.JsonFormatter(
        '%(asctime)s %(levelname)s %(name)s %(message)s'
    )
    log_handler.setFormatter(formatter)
    
    # Also log to console
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # Remove default handlers to prevent duplication
    del app.logger.handlers[:]
    
    # Configure root logger only (app.logger propagates to it)
    root_logger = logging.getLogger()
    # Clear existing handlers
    if root_logger.handlers:
        root_logger.handlers.clear()
        
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(log_handler)
    root_logger.addHandler(console_handler)
    
    # Ensure app logger propagates
    app.logger.propagate = True

def create_app(config_name=None):
    """Application factory pattern."""
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'default')
    
    app = Flask(__name__)
    configure_logging(app)
    
    cfg_class = config[config_name]
    app.config.from_object(cfg_class)
    # Run optional per-environment initialization
    if hasattr(cfg_class, 'init_app'):
        cfg_class.init_app(app)
    
    # Initialize extensions with app
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    
    # Configure login manager
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    
    # Harden session cookies
    app.config.setdefault('SESSION_COOKIE_HTTPONLY', True)
    app.config.setdefault('REMEMBER_COOKIE_HTTPONLY', True)
    # In production behind HTTPS, set these to True via environment
    app.config.setdefault('SESSION_COOKIE_SAMESITE', 'Lax')
    app.config.setdefault('REMEMBER_COOKIE_SAMESITE', 'Lax')

    # Import models so they are registered with SQLAlchemy
    from app.models import User  # noqa: F401

    @login_manager.user_loader
    def load_user(user_id):
        """Flask-Login user loader callback."""
        try:
            return User.query.get(int(user_id))
        except Exception:
            return None

    # Make csrf_token available in Jinja templates
    @app.context_processor
    def inject_csrf():
        from flask_wtf.csrf import generate_csrf
        return dict(csrf_token=generate_csrf)

    # CSRF error handler
    @app.errorhandler(CSRFError)
    def handle_csrf_error(e):
        from flask import flash, redirect, request, url_for
        flash('Security validation failed (CSRF). Please try again.', 'error')
        # Try to redirect back, else to home
        return redirect(request.referrer or url_for('main.dashboard'))

    # Register blueprints
    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    
    from app.main import bp as main_bp
    app.register_blueprint(main_bp)
    
    from app.employees import bp as employees_bp
    app.register_blueprint(employees_bp, url_prefix='/employees')
    
    from app.scraping import bp as scraping_bp
    app.register_blueprint(scraping_bp, url_prefix='/scraping')
    
    from app.analysis import bp as analysis_bp
    app.register_blueprint(analysis_bp, url_prefix='/analysis')
    
    # Create database tables
    with app.app_context():
        db.create_all()
    
    return app

"""Flask Backend Application Factory."""

from flask import Flask
from flask_cors import CORS
from prometheus_client import make_wsgi_app
from werkzeug.middleware.dispatcher import DispatcherMiddleware

from .config import Config
from .models import get_db, init_db, initialize_ai_config, initialize_admin_user
from .celery_config import make_celery
from .db_schema import init_database_schema, check_table_exists, check_admin_user_exists, get_sqlalchemy_engine


def create_app(config_class: type = Config) -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize Celery
    celery = make_celery(app)
    app.celery = celery

    # Initialize CORS
    CORS(app, resources={
        r"/api/*": {
            "origins": app.config.get("CORS_ORIGINS", "*"),
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"],
        }
    })

    # Initialize database schema with SQLAlchemy
    # This ensures all tables exist before PyDAL tries to use them
    with app.app_context():
        app.logger.info("Checking database schema...")

        # Check if critical tables exist
        engine = get_sqlalchemy_engine()

        # Check for all critical tables (not just multi-tenancy tables)
        critical_tables = [
            'users', 'tenants', 'teams', 'repo_configs', 'reviews',
            'review_comments', 'git_credentials', 'repository_members'
        ]
        tables_exist = all(check_table_exists(engine, table) for table in critical_tables)

        admin_exists = check_admin_user_exists(engine)

        # Initialize schema if any tables are missing
        # SQLAlchemy create_all() is idempotent - safe to run multiple times
        if not tables_exist:
            app.logger.info("Required tables missing, initializing database schema with SQLAlchemy...")
            init_database_schema(app)
        else:
            app.logger.info("All database tables exist")

        # Initialize PyDAL for runtime operations
        init_db(app)

        # Initialize default tenant and migrate existing data
        from .models import initialize_default_tenant
        initialize_default_tenant()

        # Initialize admin user if it doesn't exist
        if not admin_exists:
            app.logger.info("Admin user missing, creating...")
            initialize_admin_user()
        else:
            app.logger.info("Admin user exists")

    # Register blueprints - existing
    from .auth import auth_bp
    from .users import users_bp
    from .hello import hello_bp

    app.register_blueprint(auth_bp, url_prefix="/api/v1/auth")
    app.register_blueprint(users_bp, url_prefix="/api/v1/users")
    app.register_blueprint(hello_bp, url_prefix="/api/v1")

    # Register blueprints - PR Reviewer API
    from .api.v1.ai_config import ai_config_bp
    from .api.v1.analytics import analytics_bp
    from .api.v1.config import config_bp
    from .api.v1.configs import configs_bp
    from .api.v1.credentials import credentials_bp
    from .api.v1.dashboard import dashboard_bp
    from .api.v1.integrations import integrations_bp
    from .api.v1.issues import issues_bp
    from .api.v1.licenses import licenses_bp
    from .api.v1.providers import providers_bp
    from .api.v1.repos import repos_bp
    from .api.v1.repositories import repositories_bp
    from .api.v1.reviews import reviews_bp
    from .api.v1.roles import roles_bp
    from .api.v1.teams import teams_bp
    from .api.v1.tenants import tenants_bp
    from .api.v1.webhooks import webhooks_bp

    app.register_blueprint(ai_config_bp, url_prefix="/api/v1")
    app.register_blueprint(analytics_bp, url_prefix="/api/v1/analytics")
    app.register_blueprint(config_bp, url_prefix="/api/v1/config")
    app.register_blueprint(configs_bp, url_prefix="/api/v1/configs")
    app.register_blueprint(credentials_bp, url_prefix="/api/v1/credentials")
    app.register_blueprint(dashboard_bp, url_prefix="/api/v1/dashboard")
    app.register_blueprint(integrations_bp, url_prefix="/api/v1/integrations")
    app.register_blueprint(issues_bp, url_prefix="/api/v1/issues")
    app.register_blueprint(licenses_bp, url_prefix="/api/v1/licenses")
    app.register_blueprint(providers_bp, url_prefix="/api/v1/providers")
    app.register_blueprint(repos_bp, url_prefix="/api/v1/repos")
    app.register_blueprint(repositories_bp, url_prefix="/api/v1/repositories")
    app.register_blueprint(reviews_bp, url_prefix="/api/v1/reviews")
    app.register_blueprint(roles_bp, url_prefix="/api/v1/roles")
    app.register_blueprint(teams_bp, url_prefix="/api/v1/teams")
    app.register_blueprint(tenants_bp, url_prefix="/api/v1/tenants")
    app.register_blueprint(webhooks_bp, url_prefix="/api/v1/webhooks")

    # Health check endpoint
    @app.route("/healthz")
    def health_check():
        """Health check endpoint."""
        try:
            db = get_db()
            db.executesql("SELECT 1")
            return {"status": "healthy", "database": "connected"}, 200
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}, 503

    # Readiness check endpoint
    @app.route("/readyz")
    def readiness_check():
        """Readiness check endpoint."""
        return {"status": "ready"}, 200

    # Add Prometheus metrics endpoint
    app.wsgi_app = DispatcherMiddleware(
        app.wsgi_app,
        {"/metrics": make_wsgi_app()}
    )

    return app

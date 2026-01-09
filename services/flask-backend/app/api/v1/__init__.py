"""API v1 Blueprints."""

from .ai_config import ai_config_bp
from .analytics import analytics_bp
from .configs import configs_bp
from .credentials import credentials_bp
from .issues import issues_bp
from .providers import providers_bp
from .repos import repos_bp
from .reviews import reviews_bp
from .webhooks import webhooks_bp

__all__ = [
    "ai_config_bp",
    "analytics_bp",
    "configs_bp",
    "credentials_bp",
    "issues_bp",
    "providers_bp",
    "repos_bp",
    "reviews_bp",
    "webhooks_bp",
]

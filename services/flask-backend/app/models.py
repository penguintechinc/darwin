"""PyDAL Database Models."""

from datetime import datetime
from typing import Optional

from flask import Flask, g
from pydal import DAL, Field
from pydal.validators import IS_EMAIL, IS_IN_SET, IS_NOT_EMPTY, IS_JSON

from .config import Config

# Valid roles for the application
VALID_ROLES = ["admin", "maintainer", "viewer"]


def init_db(app: Flask) -> DAL:
    """Initialize database connection and define tables using PyDAL's built-in migration handling."""
    db_uri = Config.get_db_uri()

    # Initialize database with migration support
    # Note: Using fake_migrate_all=True to handle concurrent worker initialization
    # This allows multiple gunicorn workers to start simultaneously without conflicts
    # Migration files stored in /tmp since /app may be read-only in containers
    import os
    migration_folder = os.environ.get("PYDAL_MIGRATION_FOLDER", "/tmp/pydal_migrations")
    os.makedirs(migration_folder, exist_ok=True)

    # Always run migrations, PyDAL handles existing tables gracefully
    # Use fake_migrate_all=True to sync with existing schema created via SQL migrations
    # This prevents PyDAL from trying to recreate tables that already exist
    db = DAL(
        db_uri,
        pool_size=Config.DB_POOL_SIZE,
        migrate=True,
        fake_migrate_all=True,
        check_reserved=["all"],
        lazy_tables=False,
        folder=migration_folder,
    )

    # Define tenants table FIRST - Required before users due to default_tenant_id reference
    db.define_table(
        "tenants",
        Field("name", "string", length=255, unique=True, requires=IS_NOT_EMPTY()),
        Field("slug", "string", length=128, unique=True, requires=IS_NOT_EMPTY()),
        Field("description", "text"),
        Field("is_active", "boolean", default=True),
        Field("max_users", "integer", default=0),  # 0 = unlimited
        Field("max_repositories", "integer", default=0),  # 0 = unlimited
        Field("max_teams", "integer", default=0),  # 0 = unlimited
        Field("settings", "json", default={}),
        Field("created_at", "datetime", default=datetime.utcnow),
        Field("updated_at", "datetime", default=datetime.utcnow, update=datetime.utcnow),
        format="%(name)s",
    )

    # Define users table
    db.define_table(
        "users",
        Field("email", "string", length=255, unique=True, requires=[
            IS_NOT_EMPTY(error_message="Email is required"),
            IS_EMAIL(error_message="Invalid email format"),
        ]),
        Field("password_hash", "string", length=255, requires=IS_NOT_EMPTY()),
        Field("full_name", "string", length=255),
        Field("role", "string", length=50, default="viewer", requires=IS_IN_SET(
            VALID_ROLES,
            error_message=f"Role must be one of: {', '.join(VALID_ROLES)}"
        )),
        Field("global_role", "string", length=50, default="viewer", requires=IS_IN_SET(
            VALID_ROLES,
            error_message=f"Global role must be one of: {', '.join(VALID_ROLES)}"
        )),
        Field("default_tenant_id", "reference tenants", ondelete="SET NULL"),
        Field("is_active", "boolean", default=True),
        Field("created_at", "datetime", default=datetime.utcnow),
        Field("updated_at", "datetime", default=datetime.utcnow, update=datetime.utcnow),
    )

    # Define refresh tokens table for token invalidation
    db.define_table(
        "refresh_tokens",
        Field("user_id", "reference users", requires=IS_NOT_EMPTY()),
        Field("token_hash", "string", length=255, unique=True),
        Field("expires_at", "datetime"),
        Field("revoked", "boolean", default=False),
        Field("created_at", "datetime", default=datetime.utcnow),
    )

    # Define teams table - Department/Project groups within tenants
    # IMPORTANT: Must be defined before reviews and repo_configs which reference it
    db.define_table(
        "teams",
        Field("tenant_id", "reference tenants", ondelete="CASCADE", requires=IS_NOT_EMPTY()),
        Field("name", "string", length=255, requires=IS_NOT_EMPTY()),
        Field("slug", "string", length=128, requires=IS_NOT_EMPTY()),
        Field("description", "text"),
        Field("is_active", "boolean", default=True),
        Field("is_default", "boolean", default=False),  # Default team for tenant
        Field("settings", "json", default={}),
        Field("created_at", "datetime", default=datetime.utcnow),
        Field("updated_at", "datetime", default=datetime.utcnow, update=datetime.utcnow),
        format="%(name)s",
    )

    # Define custom_roles table - User-defined roles with scopes
    # IMPORTANT: Must be defined before repository_members, tenant_members, team_members which reference it
    db.define_table(
        "custom_roles",
        Field("tenant_id", "reference tenants", ondelete="CASCADE"),  # NULL = global role
        Field("team_id", "reference teams", ondelete="CASCADE"),  # NULL = not team-specific
        Field("name", "string", length=128, requires=IS_NOT_EMPTY()),
        Field("slug", "string", length=128, requires=IS_NOT_EMPTY()),
        Field("description", "text"),
        Field("role_level", "string", requires=IS_IN_SET(["global", "tenant", "team", "resource"])),
        Field("scopes", "json", requires=IS_NOT_EMPTY()),
        Field("is_active", "boolean", default=True),
        Field("created_at", "datetime", default=datetime.utcnow),
        Field("updated_at", "datetime", default=datetime.utcnow, update=datetime.utcnow),
        format="%(name)s",
    )

    # Define reviews table - Main review requests
    db.define_table(
        "reviews",
        # Multi-tenancy fields
        Field("tenant_id", "reference tenants"),
        Field("team_id", "reference teams"),
        Field("triggered_by", "reference users"),
        # Review identification
        Field("external_id", "string", length=64, unique=True),
        Field("platform", "string", requires=IS_IN_SET(["github", "gitlab"])),
        Field("repository", "string", length=255, requires=IS_NOT_EMPTY()),
        Field("pull_request_id", "integer"),
        Field("pull_request_url", "string", length=512),
        Field("base_sha", "string", length=64),
        Field("head_sha", "string", length=64),
        Field("review_type", "string", requires=IS_IN_SET(["differential", "whole"])),
        Field("categories", "json"),
        Field("ai_provider", "string", length=64),
        Field("status", "string", default="queued", requires=IS_IN_SET(
            ["queued", "in_progress", "completed", "failed", "cancelled"]
        )),
        Field("error_message", "text"),
        Field("files_reviewed", "integer", default=0),
        Field("comments_posted", "integer", default=0),
        Field("started_at", "datetime"),
        Field("completed_at", "datetime"),
        Field("created_at", "datetime", default=datetime.utcnow),
        Field("updated_at", "datetime", default=datetime.utcnow, update=datetime.utcnow),
    )

    # Define review_comments table - Individual review comments
    db.define_table(
        "review_comments",
        Field("review_id", "reference reviews", requires=IS_NOT_EMPTY()),
        Field("file_path", "string", length=512),
        Field("line_start", "integer"),
        Field("line_end", "integer"),
        Field("category", "string", requires=IS_IN_SET(
            ["security", "best_practices", "framework", "iac"]
        )),
        Field("severity", "string", requires=IS_IN_SET(
            ["critical", "major", "minor", "suggestion"]
        )),
        Field("title", "string", length=255),
        Field("body", "text"),
        Field("suggestion", "text"),
        Field("review_source", "string", length=64),
        Field("linter_rule_id", "string", length=128),
        Field("platform_comment_id", "string", length=128),
        Field("status", "string", default="open", requires=IS_IN_SET(
            ["open", "acknowledged", "fixed", "wont_fix", "false_positive"]
        )),
        Field("posted_at", "datetime"),
        Field("created_at", "datetime", default=datetime.utcnow),
    )

    # Define review_detections table - Detected languages/frameworks per review
    db.define_table(
        "review_detections",
        Field("review_id", "reference reviews", requires=IS_NOT_EMPTY()),
        Field("detection_type", "string"),
        Field("name", "string", length=128),
        Field("confidence", "double"),
        Field("file_count", "integer"),
    )

    # Define git_credentials table - Secure credential storage
    # IMPORTANT: Must be defined before repo_configs which references it
    db.define_table(
        "git_credentials",
        Field("name", "string", length=128),
        Field("git_url_pattern", "string", length=255),
        Field("auth_type", "string", requires=IS_IN_SET(["https_token", "ssh_key"])),
        Field("encrypted_credential", "blob"),
        Field("ssh_key_passphrase", "blob"),
        Field("created_by", "reference users"),
        Field("created_at", "datetime", default=datetime.utcnow),
        Field("updated_at", "datetime", default=datetime.utcnow, update=datetime.utcnow),
    )

    # Define repo_configs table - Per-repository configuration
    db.define_table(
        "repo_configs",
        # Multi-tenancy fields
        Field("tenant_id", "reference tenants", ondelete="CASCADE"),
        Field("team_id", "reference teams", ondelete="CASCADE"),
        Field("owner_id", "reference users", ondelete="SET NULL"),
        # Repository identification
        Field("platform", "string", requires=IS_IN_SET(["github", "gitlab"])),
        Field("repository", "string", length=255, requires=IS_NOT_EMPTY()),
        Field("enabled", "boolean", default=True),
        Field("auto_review", "boolean", default=True),
        Field("review_on_open", "boolean", default=True),
        Field("review_on_sync", "boolean", default=False),
        Field("default_categories", "json"),
        Field("default_ai_provider", "string", length=64),
        Field("ignored_paths", "json"),
        Field("custom_rules", "json"),
        Field("webhook_secret", "string", length=255),
        # Polling configuration
        Field("polling_enabled", "boolean", default=False),
        Field("polling_interval_minutes", "integer", default=5),
        Field("last_poll_at", "datetime"),
        # Organization grouping (for dashboard drill-down)
        Field("platform_organization", "string", length=255),
        # Display settings
        Field("display_name", "string", length=255),
        Field("description", "text"),
        Field("is_active", "boolean", default=True),
        # Credential selection
        Field("credential_id", "reference git_credentials", ondelete="SET NULL"),
        # Advanced settings
        Field("max_review_age_hours", "integer", default=168),  # 7 days
        Field("skip_patterns", "json"),
        Field("created_at", "datetime", default=datetime.utcnow),
        Field("updated_at", "datetime", default=datetime.utcnow, update=datetime.utcnow),
        format="%(platform)s/%(repository)s",
    )

    # Define repository_members table - Per-user repository access and credentials
    db.define_table(
        "repository_members",
        Field("repository_id", "reference repo_configs", ondelete="CASCADE"),
        Field("user_id", "reference users", ondelete="CASCADE"),
        Field("role", "string", length=50, default="viewer", requires=IS_IN_SET(
            ["owner", "maintainer", "viewer", "custom"]
        )),
        Field("custom_role_id", "reference custom_roles", ondelete="SET NULL"),
        Field("scopes", "json", default=[]),
        Field("personal_token_id", "reference git_credentials", ondelete="SET NULL"),
        Field("created_at", "datetime", default=datetime.utcnow),
        Field("updated_at", "datetime", default=datetime.utcnow, update=datetime.utcnow),
    )

    # Define provider_usage table - AI token usage tracking
    db.define_table(
        "provider_usage",
        Field("review_id", "reference reviews"),
        Field("provider", "string", length=64),
        Field("model", "string", length=128),
        Field("prompt_tokens", "integer"),
        Field("completion_tokens", "integer"),
        Field("total_tokens", "integer"),
        Field("latency_ms", "integer"),
        Field("cost_estimate", "double"),
        Field("created_at", "datetime", default=datetime.utcnow),
    )

    # Define ai_model_config table - AI model preferences per category
    db.define_table(
        "ai_model_config",
        Field("config_name", "string", length=128, unique=True, default="default"),
        Field("security_enabled", "boolean", default=True),
        Field("security_model", "string", length=128, default="granite-code:20b"),
        Field("best_practices_enabled", "boolean", default=True),
        Field("best_practices_model", "string", length=128, default="codestral:22b"),
        Field("framework_enabled", "boolean", default=True),
        Field("framework_model", "string", length=128, default="codestral:22b"),
        Field("iac_enabled", "boolean", default=True),
        Field("iac_model", "string", length=128, default="granite-code:20b"),
        Field("fallback_model", "string", length=128, default="starcoder2:15b"),
        Field("created_at", "datetime", default=datetime.utcnow),
        Field("updated_at", "datetime", default=datetime.utcnow, update=datetime.utcnow),
        format="%(config_name)s",
    )

    # Define license_policies table - License policy configuration
    db.define_table(
        "license_policies",
        Field("license_name", "string", length=255, unique=True, requires=IS_NOT_EMPTY()),
        Field("policy", "string", default="allowed", requires=IS_IN_SET(
            ["allowed", "blocked", "review_required"]
        )),
        Field("actions", "json", default=["warn"]),
        Field("description", "text"),
        Field("created_at", "datetime", default=datetime.utcnow),
        Field("updated_at", "datetime", default=datetime.utcnow, update=datetime.utcnow),
        format="%(license_name)s",
    )

    # Define license_detections table - Detected licenses per review
    db.define_table(
        "license_detections",
        Field("review_id", "reference reviews", requires=IS_NOT_EMPTY()),
        Field("package_name", "string", length=255),
        Field("package_version", "string", length=128),
        Field("license_name", "string", length=255),
        Field("license_source", "string", length=64),
        Field("file_path", "string", length=512),
        Field("confidence", "double"),
        Field("policy_violation", "boolean", default=False),
        Field("created_at", "datetime", default=datetime.utcnow),
    )

    # Define license_violations table - License policy violations
    db.define_table(
        "license_violations",
        Field("review_id", "reference reviews", requires=IS_NOT_EMPTY()),
        Field("detection_id", "reference license_detections"),
        Field("license_name", "string", length=255),
        Field("package_name", "string", length=255),
        Field("policy", "string"),
        Field("severity", "string", default="warning", requires=IS_IN_SET(
            ["critical", "warning", "info"]
        )),
        Field("actions_taken", "json"),
        Field("status", "string", default="open", requires=IS_IN_SET(
            ["open", "acknowledged", "resolved", "suppressed"]
        )),
        Field("created_at", "datetime", default=datetime.utcnow),
        Field("updated_at", "datetime", default=datetime.utcnow, update=datetime.utcnow),
    )

    # Define installation_config table - Installation-level configuration
    db.define_table(
        "installation_config",
        Field("config_key", "string", length=128, unique=True, requires=IS_NOT_EMPTY()),
        Field("config_value", "text"),
        Field("created_at", "datetime", default=datetime.utcnow),
        Field("updated_at", "datetime", default=datetime.utcnow, update=datetime.utcnow),
        format="%(config_key)s",
    )

    # Define tenant_members table - User-tenant associations with roles
    db.define_table(
        "tenant_members",
        Field("tenant_id", "reference tenants", ondelete="CASCADE", requires=IS_NOT_EMPTY()),
        Field("user_id", "reference users", ondelete="CASCADE", requires=IS_NOT_EMPTY()),
        Field("role", "string", length=50, default="viewer", requires=IS_IN_SET(
            ["admin", "maintainer", "viewer", "custom"]
        )),
        Field("custom_role_id", "reference custom_roles", ondelete="SET NULL"),
        Field("scopes", "json", default=[]),
        Field("is_active", "boolean", default=True),
        Field("joined_at", "datetime", default=datetime.utcnow),
        Field("created_at", "datetime", default=datetime.utcnow),
        Field("updated_at", "datetime", default=datetime.utcnow, update=datetime.utcnow),
    )

    # Define team_members table - User-team associations with roles
    db.define_table(
        "team_members",
        Field("team_id", "reference teams", ondelete="CASCADE", requires=IS_NOT_EMPTY()),
        Field("user_id", "reference users", ondelete="CASCADE", requires=IS_NOT_EMPTY()),
        Field("role", "string", length=50, default="viewer", requires=IS_IN_SET(
            ["admin", "maintainer", "viewer", "custom"]
        )),
        Field("custom_role_id", "reference custom_roles", ondelete="SET NULL"),
        Field("scopes", "json", default=[]),
        Field("is_active", "boolean", default=True),
        Field("joined_at", "datetime", default=datetime.utcnow),
        Field("created_at", "datetime", default=datetime.utcnow),
        Field("updated_at", "datetime", default=datetime.utcnow, update=datetime.utcnow),
    )

    # Define scopes table - Available permission scopes
    db.define_table(
        "scopes",
        Field("permission_scope", "string", length=128, unique=True, requires=IS_NOT_EMPTY()),
        Field("description", "text"),
        Field("category", "string", length=64),
        Field("scope_level", "string", requires=IS_IN_SET(["global", "tenant", "team", "resource"])),
        Field("created_at", "datetime", default=datetime.utcnow),
        format="%(permission_scope)s",
    )

    # Commit table definitions
    db.commit()

    # Store db instance in app
    app.config["db"] = db

    return db


def get_db() -> DAL:
    """Get database connection for current request context."""
    from flask import current_app

    if "db" not in g:
        g.db = current_app.config.get("db")
    return g.db


def get_user_by_email(email: str) -> Optional[dict]:
    """Get user by email address."""
    db = get_db()
    user = db(db.users.email == email).select().first()
    return user.as_dict() if user else None


def get_user_by_id(user_id: int) -> Optional[dict]:
    """Get user by ID."""
    db = get_db()
    user = db(db.users.id == user_id).select().first()
    return user.as_dict() if user else None


def create_user(email: str, password_hash: str, full_name: str = "",
                role: str = "viewer") -> dict:
    """Create a new user."""
    db = get_db()
    user_id = db.users.insert(
        email=email,
        password_hash=password_hash,
        full_name=full_name,
        role=role,
        is_active=True,
    )
    db.commit()
    return get_user_by_id(user_id)


def update_user(user_id: int, **kwargs) -> Optional[dict]:
    """Update user by ID."""
    db = get_db()

    # Filter allowed fields
    allowed_fields = {"email", "password_hash", "full_name", "role", "is_active"}
    update_data = {k: v for k, v in kwargs.items() if k in allowed_fields}

    if not update_data:
        return get_user_by_id(user_id)

    db(db.users.id == user_id).update(**update_data)
    db.commit()
    return get_user_by_id(user_id)


def delete_user(user_id: int) -> bool:
    """Delete user by ID."""
    db = get_db()
    deleted = db(db.users.id == user_id).delete()
    db.commit()
    return deleted > 0


def list_users(page: int = 1, per_page: int = 20) -> tuple[list[dict], int]:
    """List users with pagination."""
    db = get_db()
    offset = (page - 1) * per_page

    users = db(db.users).select(
        orderby=db.users.created_at,
        limitby=(offset, offset + per_page),
    )
    total = db(db.users).count()

    return [u.as_dict() for u in users], total


def store_refresh_token(user_id: int, token_hash: str, expires_at: datetime) -> int:
    """Store a refresh token."""
    db = get_db()
    token_id = db.refresh_tokens.insert(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    db.commit()
    return token_id


def revoke_refresh_token(token_hash: str) -> bool:
    """Revoke a refresh token."""
    db = get_db()
    updated = db(db.refresh_tokens.token_hash == token_hash).update(revoked=True)
    db.commit()
    return updated > 0


def is_refresh_token_valid(token_hash: str) -> bool:
    """Check if refresh token is valid (not revoked and not expired)."""
    db = get_db()
    token = db(
        (db.refresh_tokens.token_hash == token_hash) &
        (db.refresh_tokens.revoked == False) &
        (db.refresh_tokens.expires_at > datetime.utcnow())
    ).select().first()
    return token is not None


def revoke_all_user_tokens(user_id: int) -> int:
    """Revoke all refresh tokens for a user."""
    db = get_db()
    updated = db(db.refresh_tokens.user_id == user_id).update(revoked=True)
    db.commit()
    return updated


# ===========================
# Reviews Helper Functions
# ===========================


def create_review(external_id: str, platform: str, repository: str,
                  review_type: str, categories: list, ai_provider: str,
                  pull_request_id: Optional[int] = None,
                  pull_request_url: Optional[str] = None,
                  base_sha: Optional[str] = None,
                  head_sha: Optional[str] = None) -> dict:
    """Create a new review request."""
    db = get_db()
    review_id = db.reviews.insert(
        external_id=external_id,
        platform=platform,
        repository=repository,
        pull_request_id=pull_request_id,
        pull_request_url=pull_request_url,
        base_sha=base_sha,
        head_sha=head_sha,
        review_type=review_type,
        categories=categories,
        ai_provider=ai_provider,
        status="queued",
    )
    db.commit()
    return get_review_by_id(review_id)


def get_review_by_id(review_id: int) -> Optional[dict]:
    """Get review by ID."""
    db = get_db()
    review = db(db.reviews.id == review_id).select().first()
    return review.as_dict() if review else None


def get_review_by_external_id(external_id: str) -> Optional[dict]:
    """Get review by external ID."""
    db = get_db()
    review = db(db.reviews.external_id == external_id).select().first()
    return review.as_dict() if review else None


def update_review_status(review_id: int, status: str,
                        error_message: Optional[str] = None,
                        files_reviewed: Optional[int] = None,
                        comments_posted: Optional[int] = None) -> Optional[dict]:
    """Update review status and metrics."""
    db = get_db()
    update_data = {"status": status}

    if error_message is not None:
        update_data["error_message"] = error_message
    if files_reviewed is not None:
        update_data["files_reviewed"] = files_reviewed
    if comments_posted is not None:
        update_data["comments_posted"] = comments_posted

    # Set timestamps based on status
    if status == "in_progress":
        update_data["started_at"] = datetime.utcnow()
    elif status in ["completed", "failed", "cancelled"]:
        update_data["completed_at"] = datetime.utcnow()

    db(db.reviews.id == review_id).update(**update_data)
    db.commit()
    return get_review_by_id(review_id)


def list_reviews(platform: Optional[str] = None,
                repository: Optional[str] = None,
                status: Optional[str] = None,
                page: int = 1,
                per_page: int = 20) -> tuple[list[dict], int]:
    """List reviews with optional filtering and pagination."""
    db = get_db()
    offset = (page - 1) * per_page

    # Build query
    query = db.reviews.id > 0
    if platform:
        query &= db.reviews.platform == platform
    if repository:
        query &= db.reviews.repository == repository
    if status:
        query &= db.reviews.status == status

    reviews = db(query).select(
        orderby=~db.reviews.created_at,
        limitby=(offset, offset + per_page),
    )
    total = db(query).count()

    return [r.as_dict() for r in reviews], total


# ===========================
# Review Comments Helper Functions
# ===========================


def create_comment(review_id: int, file_path: str, line_start: int,
                  line_end: int, category: str, severity: str,
                  title: str, body: str, review_source: str,
                  suggestion: Optional[str] = None,
                  linter_rule_id: Optional[str] = None) -> dict:
    """Create a new review comment."""
    db = get_db()
    comment_id = db.review_comments.insert(
        review_id=review_id,
        file_path=file_path,
        line_start=line_start,
        line_end=line_end,
        category=category,
        severity=severity,
        title=title,
        body=body,
        review_source=review_source,
        suggestion=suggestion,
        linter_rule_id=linter_rule_id,
    )
    db.commit()
    comment = db(db.review_comments.id == comment_id).select().first()
    return comment.as_dict() if comment else None


def get_comments_by_review(review_id: int,
                          category: Optional[str] = None,
                          severity: Optional[str] = None) -> list[dict]:
    """Get all comments for a review with optional filtering."""
    db = get_db()

    query = db.review_comments.review_id == review_id
    if category:
        query &= db.review_comments.category == category
    if severity:
        query &= db.review_comments.severity == severity

    comments = db(query).select(orderby=db.review_comments.created_at)
    return [c.as_dict() for c in comments]


def update_comment_status(comment_id: int, status: str,
                         platform_comment_id: Optional[str] = None) -> Optional[dict]:
    """Update comment status and optionally set platform comment ID."""
    db = get_db()
    update_data = {"status": status}

    if platform_comment_id:
        update_data["platform_comment_id"] = platform_comment_id
        update_data["posted_at"] = datetime.utcnow()

    db(db.review_comments.id == comment_id).update(**update_data)
    db.commit()
    comment = db(db.review_comments.id == comment_id).select().first()
    return comment.as_dict() if comment else None


# ===========================
# Review Detections Helper Functions
# ===========================


def create_detection(review_id: int, detection_type: str, name: str,
                    confidence: float, file_count: int) -> dict:
    """Create a new review detection."""
    db = get_db()
    detection_id = db.review_detections.insert(
        review_id=review_id,
        detection_type=detection_type,
        name=name,
        confidence=confidence,
        file_count=file_count,
    )
    db.commit()
    detection = db(db.review_detections.id == detection_id).select().first()
    return detection.as_dict() if detection else None


def get_detections_by_review(review_id: int,
                             detection_type: Optional[str] = None) -> list[dict]:
    """Get all detections for a review with optional type filtering."""
    db = get_db()

    query = db.review_detections.review_id == review_id
    if detection_type:
        query &= db.review_detections.detection_type == detection_type

    detections = db(query).select(orderby=~db.review_detections.confidence)
    return [d.as_dict() for d in detections]


# ===========================
# Repository Config Helper Functions
# ===========================


def get_repo_config(platform: str, repository: str) -> Optional[dict]:
    """Get repository configuration."""
    db = get_db()
    config = db(
        (db.repo_configs.platform == platform) &
        (db.repo_configs.repository == repository)
    ).select().first()
    return config.as_dict() if config else None


def create_or_update_repo_config(platform: str, repository: str, **kwargs) -> dict:
    """Create or update repository configuration."""
    db = get_db()

    # Check if config exists
    existing = db(
        (db.repo_configs.platform == platform) &
        (db.repo_configs.repository == repository)
    ).select().first()

    if existing:
        # Update existing config
        db(
            (db.repo_configs.platform == platform) &
            (db.repo_configs.repository == repository)
        ).update(**kwargs)
        db.commit()
    else:
        # Create new config
        db.repo_configs.insert(
            platform=platform,
            repository=repository,
            **kwargs
        )
        db.commit()

    return get_repo_config(platform, repository)


def list_repo_configs(platform: Optional[str] = None,
                     enabled_only: bool = False) -> list[dict]:
    """List repository configurations with optional filtering."""
    db = get_db()

    query = db.repo_configs.id > 0
    if platform:
        query &= db.repo_configs.platform == platform
    if enabled_only:
        query &= db.repo_configs.enabled == True

    configs = db(query).select(orderby=db.repo_configs.repository)
    return [c.as_dict() for c in configs]


def create_repository(platform: str, repository: str, organization: Optional[str] = None,
                     credential_id: Optional[int] = None, **kwargs) -> dict:
    """Create a new repository configuration."""
    db = get_db()
    repo_id = db.repo_configs.insert(
        platform=platform,
        repository=repository,
        platform_organization=organization,
        credential_id=credential_id,
        **kwargs
    )
    db.commit()
    return get_repository_by_id(repo_id)


def get_repository_by_id(repo_id: int) -> Optional[dict]:
    """Get repository configuration by ID."""
    db = get_db()
    repo = db(db.repo_configs.id == repo_id).select().first()
    return repo.as_dict() if repo else None


def list_repositories(platform: Optional[str] = None,
                     organization: Optional[str] = None,
                     enabled: Optional[bool] = None,
                     page: int = 1,
                     per_page: int = 20) -> tuple[list[dict], int]:
    """List repositories with filtering and pagination."""
    db = get_db()
    offset = (page - 1) * per_page

    # Build query
    query = db.repo_configs.id > 0
    if platform:
        query &= db.repo_configs.platform == platform
    if organization:
        query &= db.repo_configs.platform_organization == organization
    if enabled is not None:
        query &= db.repo_configs.enabled == enabled

    repos = db(query).select(
        orderby=~db.repo_configs.created_at,
        limitby=(offset, offset + per_page),
    )
    total = db(query).count()

    return [r.as_dict() for r in repos], total


def update_repository(repo_id: int, **kwargs) -> Optional[dict]:
    """Update repository configuration."""
    db = get_db()
    db(db.repo_configs.id == repo_id).update(**kwargs)
    db.commit()
    return get_repository_by_id(repo_id)


def delete_repository(repo_id: int) -> bool:
    """Delete repository configuration."""
    db = get_db()
    result = db(db.repo_configs.id == repo_id).delete()
    db.commit()
    return result > 0


def get_repositories_by_organization(platform: str, organization: str) -> list[dict]:
    """Get all repositories for a specific platform and organization."""
    db = get_db()
    repos = db(
        (db.repo_configs.platform == platform) &
        (db.repo_configs.platform_organization == organization)
    ).select(orderby=db.repo_configs.repository)
    return [r.as_dict() for r in repos]


def get_unique_organizations() -> list[dict]:
    """Get list of unique organizations grouped by platform."""
    db = get_db()
    # Query for unique platform/organization combinations
    rows = db(db.repo_configs.platform_organization != None).select(
        db.repo_configs.platform,
        db.repo_configs.platform_organization,
        distinct=True,
        orderby=db.repo_configs.platform | db.repo_configs.platform_organization
    )

    # Group by platform
    result = {}
    for row in rows:
        platform = row.platform
        org = row.platform_organization
        if platform not in result:
            result[platform] = []
        if org and org not in result[platform]:
            result[platform].append(org)

    return result


# ===========================
# Provider Usage Helper Functions
# ===========================


def create_provider_usage(review_id: Optional[int], provider: str, model: str,
                         prompt_tokens: int, completion_tokens: int,
                         latency_ms: int, cost_estimate: float) -> dict:
    """Track AI provider usage."""
    db = get_db()
    total_tokens = prompt_tokens + completion_tokens

    usage_id = db.provider_usage.insert(
        review_id=review_id,
        provider=provider,
        model=model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        latency_ms=latency_ms,
        cost_estimate=cost_estimate,
    )
    db.commit()
    usage = db(db.provider_usage.id == usage_id).select().first()
    return usage.as_dict() if usage else None


def get_usage_by_review(review_id: int) -> list[dict]:
    """Get all provider usage records for a review."""
    db = get_db()
    usage = db(db.provider_usage.review_id == review_id).select(
        orderby=db.provider_usage.created_at
    )
    return [u.as_dict() for u in usage]


def get_usage_stats(provider: Optional[str] = None,
                   start_date: Optional[datetime] = None,
                   end_date: Optional[datetime] = None) -> dict:
    """Get aggregate usage statistics."""
    db = get_db()

    query = db.provider_usage.id > 0
    if provider:
        query &= db.provider_usage.provider == provider
    if start_date:
        query &= db.provider_usage.created_at >= start_date
    if end_date:
        query &= db.provider_usage.created_at <= end_date

    stats = db(query).select(
        db.provider_usage.total_tokens.sum(),
        db.provider_usage.cost_estimate.sum(),
        db.provider_usage.id.count(),
    ).first()

    return {
        "total_tokens": stats[db.provider_usage.total_tokens.sum()] or 0,
        "total_cost": stats[db.provider_usage.cost_estimate.sum()] or 0.0,
        "total_requests": stats[db.provider_usage.id.count()] or 0,
    }


# ===========================
# Git Credentials Helper Functions
# ===========================


def store_credential(name: str, git_url_pattern: str, auth_type: str,
                    encrypted_credential: bytes,
                    ssh_key_passphrase: Optional[bytes] = None,
                    created_by: Optional[int] = None) -> dict:
    """Store a new git credential."""
    db = get_db()
    cred_id = db.git_credentials.insert(
        name=name,
        git_url_pattern=git_url_pattern,
        auth_type=auth_type,
        encrypted_credential=encrypted_credential,
        ssh_key_passphrase=ssh_key_passphrase,
        created_by=created_by,
    )
    db.commit()
    cred = db(db.git_credentials.id == cred_id).select().first()
    return cred.as_dict() if cred else None


def get_credentials(git_url_pattern: Optional[str] = None) -> list[dict]:
    """Get git credentials, optionally filtered by URL pattern."""
    db = get_db()

    if git_url_pattern:
        query = db.git_credentials.git_url_pattern == git_url_pattern
    else:
        query = db.git_credentials.id > 0

    credentials = db(query).select(orderby=db.git_credentials.name)
    return [c.as_dict() for c in credentials]


def delete_credential(cred_id: int) -> bool:
    """Delete a git credential by ID."""
    db = get_db()
    deleted = db(db.git_credentials.id == cred_id).delete()
    db.commit()
    return deleted > 0


# ===========================
# License Policy Helper Functions
# ===========================


def create_license_policy(license_name: str, policy: str, actions: list[str],
                         description: str = "") -> dict:
    """Create or update a license policy."""
    db = get_db()

    existing = db(db.license_policies.license_name == license_name).select().first()

    if existing:
        db(db.license_policies.license_name == license_name).update(
            policy=policy,
            actions=actions,
            description=description,
        )
        policy_id = existing.id
    else:
        policy_id = db.license_policies.insert(
            license_name=license_name,
            policy=policy,
            actions=actions,
            description=description,
        )

    db.commit()
    return get_license_policy(license_name)


def get_license_policy(license_name: str) -> Optional[dict]:
    """Get license policy by name."""
    db = get_db()
    policy = db(db.license_policies.license_name == license_name).select().first()
    return policy.as_dict() if policy else None


def list_license_policies() -> list[dict]:
    """List all license policies."""
    db = get_db()
    policies = db(db.license_policies).select(orderby=db.license_policies.license_name)
    return [p.as_dict() for p in policies]


def delete_license_policy(license_name: str) -> bool:
    """Delete a license policy."""
    db = get_db()
    deleted = db(db.license_policies.license_name == license_name).delete()
    db.commit()
    return deleted > 0


def record_license_detection(review_id: int, package_name: str, package_version: str,
                            license_name: str, license_source: str, file_path: str,
                            confidence: float) -> dict:
    """Record a license detection."""
    db = get_db()

    # Check if this license violates policy
    policy = get_license_policy(license_name)
    policy_violation = policy and policy.get("policy") == "blocked"

    detection_id = db.license_detections.insert(
        review_id=review_id,
        package_name=package_name,
        package_version=package_version,
        license_name=license_name,
        license_source=license_source,
        file_path=file_path,
        confidence=confidence,
        policy_violation=policy_violation,
    )
    db.commit()

    # Create violation record if policy is blocked or review_required
    if policy and policy.get("policy") in ["blocked", "review_required"]:
        severity = "critical" if policy.get("policy") == "blocked" else "warning"
        db.license_violations.insert(
            review_id=review_id,
            detection_id=detection_id,
            license_name=license_name,
            package_name=package_name,
            policy=policy.get("policy"),
            severity=severity,
            actions_taken=policy.get("actions", []),
        )
        db.commit()

    detection = db(db.license_detections.id == detection_id).select().first()
    return detection.as_dict() if detection else None


def get_review_license_violations(review_id: int) -> list[dict]:
    """Get all license violations for a review."""
    db = get_db()
    violations = db(db.license_violations.review_id == review_id).select(
        orderby=~db.license_violations.severity
    )
    return [v.as_dict() for v in violations]


def update_violation_status(violation_id: int, status: str) -> Optional[dict]:
    """Update license violation status."""
    db = get_db()
    db(db.license_violations.id == violation_id).update(status=status)
    db.commit()
    violation = db(db.license_violations.id == violation_id).select().first()
    return violation.as_dict() if violation else None


# ===========================
# Installation Config Helper Functions
# ===========================


def get_config_value(key: str, default: Optional[str] = None) -> Optional[str]:
    """
    Get installation config value with fallback to default.

    Returns the default value when installation_config table doesn't exist.

    Args:
        key: Configuration key to retrieve
        default: Default value if key not found or table doesn't exist

    Returns:
        Configuration value or default
    """
    try:
        db = get_db()
        config = db(db.installation_config.config_key == key).select().first()
        return config.config_value if config else default
    except Exception as e:
        # Handle missing installation_config table
        error_str = str(e).lower()
        if "undefined table" in error_str or "does not exist" in error_str or "no such table" in error_str:
            # Table doesn't exist yet, return default value
            return default
        else:
            # Re-raise other types of database errors
            raise


def set_config_value(key: str, value: str) -> None:
    """
    Set installation config value with graceful fallback.

    Silently skips when installation_config table doesn't exist.

    Args:
        key: Configuration key to set
        value: Configuration value to store
    """
    try:
        db = get_db()

        existing = db(db.installation_config.config_key == key).select().first()

        if existing:
            db(db.installation_config.config_key == key).update(config_value=value)
        else:
            db.installation_config.insert(config_key=key, config_value=value)

        db.commit()
    except Exception as e:
        # Handle missing installation_config table
        error_str = str(e).lower()
        if "undefined table" in error_str or "does not exist" in error_str or "no such table" in error_str:
            # Table doesn't exist yet, silently skip (will be available after migrations)
            pass
        else:
            # Re-raise other types of database errors
            raise


def get_repo_count() -> int:
    """Get count of unique repositories configured."""
    db = get_db()
    return db(db.repo_configs).count()


def check_repo_limit(has_professional_license: bool) -> tuple[bool, int, int]:
    """
    Check if repo limit is reached.

    Returns:
        Tuple of (can_add_repo, current_count, limit)
    """
    current_count = get_repo_count()

    if has_professional_license:
        return True, current_count, -1  # -1 means unlimited

    free_limit = 3
    can_add = current_count < free_limit

    return can_add, current_count, free_limit


# ===========================
# AI Configuration Helper Functions
# ===========================


def get_ai_enabled() -> bool:
    """
    Get AI enabled status with fallback hierarchy.

    Priority: Database -> Environment -> Default (True)

    Returns:
        bool: True if AI is enabled, False otherwise
    """
    try:
        # Check database first
        db_value = get_config_value("ai_enabled", default=None)
        if db_value is not None:
            return db_value.lower() == "true"
    except Exception as e:
        # Handle missing installation_config table
        error_str = str(e).lower()
        if "undefined table" in error_str or "does not exist" in error_str or "no such table" in error_str:
            # Table doesn't exist yet, fall back to environment variable
            pass
        else:
            # Re-raise other types of database errors
            raise

    # Fall back to environment variable
    return Config.AI_ENABLED


def set_ai_enabled(enabled: bool) -> None:
    """
    Set AI enabled status in database.

    Args:
        enabled: True to enable AI, False to disable
    """
    try:
        set_config_value("ai_enabled", "true" if enabled else "false")
    except Exception as e:
        # Handle missing installation_config table
        error_str = str(e).lower()
        if "undefined table" in error_str or "does not exist" in error_str or "no such table" in error_str:
            # Table doesn't exist yet, silently skip (will be available after migrations)
            pass
        else:
            # Re-raise other types of database errors
            raise


def delete_ai_config() -> None:
    """
    Delete AI config from database, reverting to environment variable default.
    """
    try:
        db = get_db()
        db(db.installation_config.config_key == "ai_enabled").delete()
        db.commit()
    except Exception as e:
        # Handle missing installation_config table
        error_str = str(e).lower()
        if "undefined table" in error_str or "does not exist" in error_str or "no such table" in error_str:
            # Table doesn't exist yet, silently succeed (nothing to delete)
            pass
        else:
            # Re-raise other types of database errors
            raise


def get_ai_config_source() -> str:
    """
    Get the source of the current AI configuration.

    Returns:
        str: "database", "environment", or "default"
    """
    try:
        db_value = get_config_value("ai_enabled", default=None)
        if db_value is not None:
            return "database"
    except Exception as e:
        # Handle missing installation_config table
        error_str = str(e).lower()
        if "undefined table" in error_str or "does not exist" in error_str or "no such table" in error_str:
            # Table doesn't exist yet, check environment or return default
            pass
        else:
            # Re-raise other types of database errors
            raise

    # Check if environment variable is set
    import os
    if os.getenv("AI_ENABLED") is not None:
        return "environment"

    return "default"


def initialize_ai_config() -> None:
    """
    Initialize AI config with default if not exists.

    This is called on application startup to ensure the config key exists.
    If no database value exists, it creates one based on the environment variable.

    Handles the case where the installation_config table doesn't exist yet
    (on first startup or during migrations).
    """
    db = get_db()
    try:
        existing = get_config_value("ai_enabled", default=None)
        if existing is None:
            # Initialize with environment variable or default
            default_value = "true" if Config.AI_ENABLED else "false"
            set_config_value("ai_enabled", default_value)
    except Exception as e:
        # Rollback the transaction to clear error state
        db.rollback()
        # Table doesn't exist yet - this is normal on first startup
        # The table will be created on next restart or config can be set via API
        error_str = str(e).lower()
        if "undefined table" in error_str or "does not exist" in error_str or "no such table" in error_str or "failed sql transaction" in error_str:
            print(f"Installation config table not yet created, skipping initialization. "
                  f"AI configuration can be set later via API.")
        else:
            # Re-raise other types of database errors
            raise


def initialize_admin_user() -> None:
    """Initialize default admin user in default tenant if none exists.

    Creates admin user with:
    - email: admin@localhost.local
    - password: admin123 (bcrypt hashed)
    - role: admin
    - global_role: admin
    - default_tenant_id: 1 (default tenant)

    Adds admin to default tenant (id=1) as admin role
    Adds admin to default team (id=1) as admin role

    Only creates if admin doesn't already exist (checked by email).
    """
    from .auth import hash_password

    db = get_db()

    try:
        admin_email = "admin@localhost.local"

        # Check if admin already exists by email
        existing_admin = db(db.users.email == admin_email).select().first()
        if existing_admin:
            print(f"Admin user already exists: {admin_email} (ID: {existing_admin.id})")
            return

        print(f"No admin user found, creating default admin user: {admin_email}")

        # Ensure default tenant exists
        default_tenant = db(db.tenants.slug == "default").select().first()
        if not default_tenant:
            print("Creating default tenant...")
            tenant_id = db.tenants.insert(
                name="Default",
                slug="default",
                description="Default tenant for all users",
                is_active=True,
                max_users=0,
                max_repositories=0,
                max_teams=0,
                settings={},
            )
            db.commit()
            print(f"Default tenant created with ID: {tenant_id}")

            # Create default team for this tenant
            print("Creating default team...")
            team_id = db.teams.insert(
                tenant_id=tenant_id,
                name="Default",
                slug="default",
                description="Default team for all tenant members",
                is_active=True,
                is_default=True,
                settings={},
            )
            db.commit()
            print(f"Default team created with ID: {team_id}")
        else:
            tenant_id = default_tenant.id
            print(f"Using existing default tenant (ID: {tenant_id})")

            # Check if default team exists
            default_team = db(
                (db.teams.tenant_id == tenant_id) & (db.teams.is_default == True)
            ).select().first()
            if not default_team:
                print("Creating default team...")
                team_id = db.teams.insert(
                    tenant_id=tenant_id,
                    name="Default",
                    slug="default",
                    description="Default team for all tenant members",
                    is_active=True,
                    is_default=True,
                    settings={},
                )
                db.commit()
                print(f"Default team created with ID: {team_id}")
            else:
                team_id = default_team.id
                print(f"Using existing default team (ID: {team_id})")

        # Create admin user
        print(f"Creating admin user: {admin_email}")
        user_id = db.users.insert(
            email=admin_email,
            password_hash=hash_password("admin123"),
            full_name="Administrator",
            role="admin",
            global_role="admin",
            default_tenant_id=tenant_id,
            is_active=True,
        )
        db.commit()
        print(f"Admin user created with ID: {user_id}")

        # Add admin to default tenant
        print(f"Adding admin to default tenant (ID: {tenant_id})...")
        tenant_member_id = db.tenant_members.insert(
            tenant_id=tenant_id,
            user_id=user_id,
            role="admin",
            is_active=True,
        )
        db.commit()
        print(f"Admin added to tenant with membership ID: {tenant_member_id}")

        # Add admin to default team
        print(f"Adding admin to default team (ID: {team_id})...")
        team_member_id = db.team_members.insert(
            team_id=team_id,
            user_id=user_id,
            role="admin",
            is_active=True,
        )
        db.commit()
        print(f"Admin added to team with membership ID: {team_member_id}")

        print(f"Default admin user initialized: {admin_email} / admin123")
        print("IMPORTANT: Change the default password immediately after first login!")

    except Exception as e:
        # Rollback the transaction to clear error state
        db.rollback()
        # Table doesn't exist yet - this is normal on first startup
        error_str = str(e).lower()
        if "undefined table" in error_str or "does not exist" in error_str or "no such table" in error_str or "failed sql transaction" in error_str:
            print(f"Required tables not yet created, skipping admin user initialization. "
                  f"Admin user will be created on next restart.")
        else:
            # Re-raise other types of database errors
            raise


def initialize_default_tenant() -> None:
    """Create default tenant and team, migrate existing data."""
    from .auth import hash_password

    db = get_db()

    try:
        # Check if default tenant exists
        default_tenant = db(db.tenants.slug == "default").select().first()

        if not default_tenant:
            print("Creating default tenant...")
            tenant_id = db.tenants.insert(
                name="Default",
                slug="default",
                description="Default tenant for all users",
                is_active=True,
                max_users=0,  # Unlimited
                max_repositories=0,  # Unlimited
                max_teams=0,  # Unlimited
                settings={},
            )
            db.commit()
            print(f"Default tenant created with ID: {tenant_id}")

            # Create default team for this tenant
            team_id = db.teams.insert(
                tenant_id=tenant_id,
                name="Default",
                slug="default",
                description="Default team for all tenant members",
                is_active=True,
                is_default=True,
                settings={},
            )
            db.commit()
            print(f"Default team created with ID: {team_id}")

            # Migrate all existing users to default tenant/team
            users = db(db.users.id > 0).select()
            for user in users:
                # Determine role based on existing user role
                tenant_role = "admin" if user.role == "admin" else "viewer"
                team_role = "admin" if user.role == "admin" else "viewer"

                # Add user to default tenant
                db.tenant_members.insert(
                    tenant_id=tenant_id,
                    user_id=user.id,
                    role=tenant_role,
                    is_active=True,
                )

                # Add user to default team
                db.team_members.insert(
                    team_id=team_id,
                    user_id=user.id,
                    role=team_role,
                    is_active=True,
                )

                # Set default tenant for user
                db(db.users.id == user.id).update(
                    default_tenant_id=tenant_id,
                    global_role=user.role,  # Copy role to global_role
                )

            db.commit()
            print(f"Migrated {len(users)} existing users to default tenant/team")

            # Migrate all existing repositories to default team
            repos = db(db.repo_configs.id > 0).select()
            for repo in repos:
                db(db.repo_configs.id == repo.id).update(
                    tenant_id=tenant_id,
                    team_id=team_id,
                )
            db.commit()
            print(f"Migrated {len(repos)} existing repositories to default team")

            # Migrate all existing reviews to default tenant/team
            reviews = db(db.reviews.id > 0).select()
            for review in reviews:
                db(db.reviews.id == review.id).update(
                    tenant_id=tenant_id,
                    team_id=team_id,
                )
            db.commit()
            print(f"Migrated {len(reviews)} existing reviews to default tenant/team")

            print("Default tenant migration completed successfully")
        else:
            print(f"Default tenant already exists (ID: {default_tenant.id})")

    except Exception as e:
        db.rollback()
        error_str = str(e).lower()
        if "undefined table" in error_str or "does not exist" in error_str or "no such table" in error_str:
            print("Multi-tenancy tables not yet created, skipping default tenant initialization.")
        else:
            print(f"Error initializing default tenant: {e}")
            raise

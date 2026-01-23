"""SQLAlchemy Models - For schema definition and migrations only.

DO NOT use these models for runtime queries. Use PyDAL models instead.
SQLAlchemy is ONLY for:
1. Database initialization
2. Schema creation
3. Database migrations via Alembic

Runtime operations should use PyDAL (app/models.py).
"""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    LargeBinary,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from .base import Base


class User(Base):
    """User table - authentication and authorization."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255))
    role = Column(String(50), default="viewer", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    refresh_tokens = relationship(
        "RefreshToken", back_populates="user", cascade="all, delete-orphan"
    )
    git_credentials = relationship(
        "GitCredential", back_populates="creator", cascade="all, delete-orphan"
    )


class RefreshToken(Base):
    """Refresh token table - for token invalidation."""

    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    token_hash = Column(String(255), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    revoked = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="refresh_tokens")


class Review(Base):
    """Review table - main review requests."""

    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, autoincrement=True)
    external_id = Column(String(64), unique=True, nullable=False, index=True)
    platform = Column(String(20), nullable=False, index=True)
    repository = Column(String(255), nullable=False, index=True)
    pull_request_id = Column(Integer)
    pull_request_url = Column(String(512))
    base_sha = Column(String(64))
    head_sha = Column(String(64))
    review_type = Column(String(20), nullable=False)
    categories = Column(JSON)
    ai_provider = Column(String(64))
    status = Column(String(20), default="queued", nullable=False, index=True)
    error_message = Column(Text)
    files_reviewed = Column(Integer, default=0)
    comments_posted = Column(Integer, default=0)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    comments = relationship(
        "ReviewComment", back_populates="review", cascade="all, delete-orphan"
    )
    detections = relationship(
        "ReviewDetection", back_populates="review", cascade="all, delete-orphan"
    )
    provider_usage = relationship(
        "ProviderUsage", back_populates="review", cascade="all, delete-orphan"
    )
    license_detections = relationship(
        "LicenseDetection", back_populates="review", cascade="all, delete-orphan"
    )
    license_violations = relationship(
        "LicenseViolation", back_populates="review", cascade="all, delete-orphan"
    )


class ReviewComment(Base):
    """Review comments table - individual review comments."""

    __tablename__ = "review_comments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    review_id = Column(Integer, ForeignKey("reviews.id"), nullable=False, index=True)
    file_path = Column(String(512), index=True)
    line_start = Column(Integer)
    line_end = Column(Integer)
    category = Column(String(50), index=True)
    severity = Column(String(20), index=True)
    title = Column(String(255))
    body = Column(Text)
    suggestion = Column(Text)
    source = Column(String(64))
    linter_rule_id = Column(String(128))
    platform_comment_id = Column(String(128))
    status = Column(String(20), default="open", index=True)
    posted_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    review = relationship("Review", back_populates="comments")


class ReviewDetection(Base):
    """Review detections table - detected languages/frameworks per review."""

    __tablename__ = "review_detections"

    id = Column(Integer, primary_key=True, autoincrement=True)
    review_id = Column(Integer, ForeignKey("reviews.id"), nullable=False, index=True)
    detection_type = Column(String(50), index=True)
    name = Column(String(128))
    confidence = Column(Float)
    file_count = Column(Integer)

    # Relationships
    review = relationship("Review", back_populates="detections")


class RepoConfig(Base):
    """Repository configuration table - per-repository settings."""

    __tablename__ = "repo_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    platform = Column(String(20), nullable=False, index=True)
    repository = Column(String(255), nullable=False, index=True)
    enabled = Column(Boolean, default=True, nullable=False)
    auto_review = Column(Boolean, default=True)
    review_on_open = Column(Boolean, default=True)
    review_on_sync = Column(Boolean, default=False)
    default_categories = Column(JSON)
    default_ai_provider = Column(String(64))
    ignored_paths = Column(JSON)
    custom_rules = Column(JSON)
    webhook_secret = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class ProviderUsage(Base):
    """Provider usage table - AI token usage tracking."""

    __tablename__ = "provider_usage"

    id = Column(Integer, primary_key=True, autoincrement=True)
    review_id = Column(Integer, ForeignKey("reviews.id"), index=True)
    provider = Column(String(64), index=True)
    model = Column(String(128))
    prompt_tokens = Column(Integer)
    completion_tokens = Column(Integer)
    total_tokens = Column(Integer)
    latency_ms = Column(Integer)
    cost_estimate = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    review = relationship("Review", back_populates="provider_usage")


class GitCredential(Base):
    """Git credentials table - secure credential storage."""

    __tablename__ = "git_credentials"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(128))
    git_url_pattern = Column(String(255), index=True)
    auth_type = Column(String(20), nullable=False)
    encrypted_credential = Column(LargeBinary)
    ssh_key_passphrase = Column(LargeBinary)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    creator = relationship("User", back_populates="git_credentials")


class AIModelConfig(Base):
    """AI model configuration table - AI model preferences per category."""

    __tablename__ = "ai_model_config"

    id = Column(Integer, primary_key=True, autoincrement=True)
    config_name = Column(
        String(128), unique=True, default="default", nullable=False, index=True
    )
    security_enabled = Column(Boolean, default=True)
    security_model = Column(String(128), default="granite-code:34b")
    best_practices_enabled = Column(Boolean, default=True)
    best_practices_model = Column(String(128), default="llama3.3:70b")
    framework_enabled = Column(Boolean, default=True)
    framework_model = Column(String(128), default="codestral:22b")
    iac_enabled = Column(Boolean, default=True)
    iac_model = Column(String(128), default="granite-code:20b")
    fallback_model = Column(String(128), default="starcoder2:15b")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class LicensePolicy(Base):
    """License policy table - license policy configuration."""

    __tablename__ = "license_policies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    license_name = Column(String(255), unique=True, nullable=False, index=True)
    policy = Column(String(20), default="allowed", nullable=False)
    actions = Column(JSON, default=["warn"])
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class LicenseDetection(Base):
    """License detection table - detected licenses per review."""

    __tablename__ = "license_detections"

    id = Column(Integer, primary_key=True, autoincrement=True)
    review_id = Column(Integer, ForeignKey("reviews.id"), nullable=False, index=True)
    package_name = Column(String(255), index=True)
    package_version = Column(String(128))
    license_name = Column(String(255), index=True)
    license_source = Column(String(64))
    file_path = Column(String(512))
    confidence = Column(Float)
    policy_violation = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    review = relationship("Review", back_populates="license_detections")


class LicenseViolation(Base):
    """License violation table - license policy violations."""

    __tablename__ = "license_violations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    review_id = Column(Integer, ForeignKey("reviews.id"), nullable=False, index=True)
    detection_id = Column(Integer, ForeignKey("license_detections.id"))
    license_name = Column(String(255), index=True)
    package_name = Column(String(255))
    policy = Column(String(20))
    severity = Column(String(20), default="warning", index=True)
    actions_taken = Column(JSON)
    status = Column(String(20), default="open", index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    review = relationship("Review", back_populates="license_violations")


class InstallationConfig(Base):
    """Installation configuration table - installation-level settings."""

    __tablename__ = "installation_config"

    id = Column(Integer, primary_key=True, autoincrement=True)
    config_key = Column(String(128), unique=True, nullable=False, index=True)
    config_value = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

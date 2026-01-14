"""Repository Management API - CRUD endpoints for repository configurations."""

from flask import Blueprint, jsonify, request
from typing import Any

from ...middleware import auth_required, admin_required, role_required, get_current_user
from ...models import (
    create_repository,
    get_repository_by_id,
    list_repositories,
    update_repository,
    delete_repository,
    get_repositories_by_organization,
    get_unique_organizations,
)

repositories_bp = Blueprint("repositories", __name__)


@repositories_bp.route("", methods=["GET"])
@auth_required
def list_repositories_endpoint() -> tuple[dict[str, Any], int]:
    """
    List repositories with optional filtering and pagination.

    Query Parameters:
        platform: Filter by platform (github, gitlab, git)
        organization: Filter by organization
        enabled: Filter by enabled status (true/false)
        page: Page number (default: 1)
        per_page: Results per page (default: 20, max: 100)

    Returns:
        JSON response with repositories list and pagination info
    """
    # Get query parameters
    platform = request.args.get("platform")
    organization = request.args.get("organization")
    enabled_str = request.args.get("enabled")
    page = int(request.args.get("page", 1))
    per_page = min(int(request.args.get("per_page", 20)), 100)

    # Parse enabled parameter
    enabled = None
    if enabled_str is not None:
        enabled = enabled_str.lower() in ("true", "1", "yes")

    # Get repositories
    repositories, total = list_repositories(
        platform=platform,
        organization=organization,
        enabled=enabled,
        page=page,
        per_page=per_page,
    )

    # Calculate pagination metadata
    pages = (total + per_page - 1) // per_page  # Ceiling division

    return jsonify({
        "repositories": repositories,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": pages,
        }
    }), 200


@repositories_bp.route("", methods=["POST"])
@auth_required
@role_required("admin", "maintainer")
def create_repository_endpoint() -> tuple[dict[str, Any], int]:
    """
    Create a new repository configuration.

    Request Body:
        platform (required): github, gitlab, or git
        repository (required): Repository identifier
        platform_organization (optional): Organization name
        display_name (optional): Display name
        description (optional): Description
        enabled (optional): Enable repository (default: true)
        polling_enabled (optional): Enable polling (default: false)
        polling_interval_minutes (optional): Polling interval (default: 5)
        auto_review (optional): Auto-review enabled (default: true)
        credential_id (optional): Credential ID to use
        default_categories (optional): Default review categories
        default_ai_provider (optional): Default AI provider

    Returns:
        JSON response with created repository
    """
    data = request.get_json()

    # Validate required fields
    if not data or "platform" not in data or "repository" not in data:
        return jsonify({"error": "Missing required fields: platform, repository"}), 400

    if data["platform"] not in ["github", "gitlab", "git"]:
        return jsonify({"error": "Invalid platform. Must be: github, gitlab, or git"}), 400

    try:
        repository = create_repository(
            platform=data["platform"],
            repository=data["repository"],
            organization=data.get("platform_organization"),
            credential_id=data.get("credential_id"),
            display_name=data.get("display_name"),
            description=data.get("description"),
            enabled=data.get("enabled", True),
            polling_enabled=data.get("polling_enabled", False),
            polling_interval_minutes=data.get("polling_interval_minutes", 5),
            auto_review=data.get("auto_review", True),
            review_on_open=data.get("review_on_open", True),
            review_on_sync=data.get("review_on_sync", False),
            default_categories=data.get("default_categories", ["security", "best_practices"]),
            default_ai_provider=data.get("default_ai_provider", "ollama"),
        )
        return jsonify(repository), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@repositories_bp.route("/<int:repo_id>", methods=["GET"])
@auth_required
def get_repository_endpoint(repo_id: int) -> tuple[dict[str, Any], int]:
    """
    Get repository configuration by ID.

    Path Parameters:
        repo_id: Repository ID

    Returns:
        JSON response with repository details
    """
    repository = get_repository_by_id(repo_id)
    if not repository:
        return jsonify({"error": "Repository not found"}), 404

    return jsonify(repository), 200


@repositories_bp.route("/<int:repo_id>", methods=["PUT"])
@auth_required
@role_required("admin", "maintainer")
def update_repository_endpoint(repo_id: int) -> tuple[dict[str, Any], int]:
    """
    Update repository configuration.

    Path Parameters:
        repo_id: Repository ID

    Request Body:
        Any repository fields to update

    Returns:
        JSON response with updated repository
    """
    # Check if repository exists
    existing = get_repository_by_id(repo_id)
    if not existing:
        return jsonify({"error": "Repository not found"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    # Validate platform if provided
    if "platform" in data and data["platform"] not in ["github", "gitlab", "git"]:
        return jsonify({"error": "Invalid platform. Must be: github, gitlab, or git"}), 400

    try:
        repository = update_repository(repo_id, **data)
        return jsonify(repository), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@repositories_bp.route("/<int:repo_id>", methods=["DELETE"])
@auth_required
@admin_required
def delete_repository_endpoint(repo_id: int) -> tuple[dict[str, Any], int]:
    """
    Delete repository configuration.

    Path Parameters:
        repo_id: Repository ID

    Returns:
        JSON response with success message
    """
    # Check if repository exists
    existing = get_repository_by_id(repo_id)
    if not existing:
        return jsonify({"error": "Repository not found"}), 404

    try:
        success = delete_repository(repo_id)
        if success:
            return jsonify({"message": "Repository deleted successfully"}), 200
        else:
            return jsonify({"error": "Failed to delete repository"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@repositories_bp.route("/organizations", methods=["GET"])
@auth_required
def list_organizations_endpoint() -> tuple[dict[str, Any], int]:
    """
    Get list of unique organizations grouped by platform.

    Returns:
        JSON response with organizations grouped by platform
    """
    try:
        organizations = get_unique_organizations()
        return jsonify({"organizations": organizations}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

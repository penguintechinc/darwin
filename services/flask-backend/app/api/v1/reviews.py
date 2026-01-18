"""Review API Endpoints - POST/GET/retry reviews."""

from flask import Blueprint, jsonify, request
from datetime import datetime

from ...middleware import auth_required, role_required, get_current_user
from ...rbac import get_user_tenant_filter
from ...models import (
    create_review,
    get_review_by_id,
    get_review_by_external_id,
    list_reviews,
    update_review_status,
    get_comments_by_review,
    get_detections_by_review,
    get_usage_by_review,
    get_db,
    get_ai_enabled,
    get_repo_config,
)

reviews_bp = Blueprint("reviews", __name__, url_prefix="/api/v1/reviews")


@reviews_bp.route("", methods=["POST"])
@auth_required
@role_required("admin", "maintainer")
def create_review_request():
    """Create a new review request with tenant/team context."""
    data = request.get_json()

    if not data:
        return jsonify({"error": "Request body required"}), 400

    # Validate required fields
    required_fields = ["external_id", "platform", "repository", "review_type", "ai_provider"]
    for field in required_fields:
        if field not in data or not data[field]:
            return jsonify({"error": f"Missing required field: {field}"}), 400

    # Validate enums
    if data.get("platform") not in ["github", "gitlab"]:
        return jsonify({"error": "Platform must be 'github' or 'gitlab'"}), 400

    if data.get("review_type") not in ["differential", "whole"]:
        return jsonify({"error": "Review type must be 'differential' or 'whole'"}), 400

    # Check for existing external_id
    existing = get_review_by_external_id(data.get("external_id"))
    if existing:
        return jsonify({"error": "Review with this external_id already exists"}), 409

    # Check if AI is enabled if AI provider requested
    if data.get("ai_provider") and not get_ai_enabled():
        return jsonify({
            "error": "AI reviews are currently disabled. Only linter reviews are available.",
            "ai_enabled": False
        }), 400

    # Get current user for tenant/team context and triggered_by
    user = get_current_user()
    if not user:
        return jsonify({"error": "User context required"}), 401

    user_id = user.get("id")

    # Get repository config to extract tenant_id and team_id
    repo_config = get_repo_config(data.get("platform"), data.get("repository"))
    if not repo_config:
        return jsonify({
            "error": "Repository configuration not found",
            "details": f"No config for {data.get('platform')}/{data.get('repository')}"
        }), 404

    tenant_id = repo_config.get("tenant_id")
    team_id = repo_config.get("team_id")

    # Verify tenant isolation - user should only create reviews for their own tenant
    user_tenant_filter = get_user_tenant_filter(user_id)
    if user_tenant_filter is not None and user_tenant_filter != tenant_id:
        return jsonify({
            "error": "Access denied - review does not belong to your tenant",
            "tenant_id": tenant_id,
            "user_tenant_id": user_tenant_filter,
        }), 403

    # Create review
    categories = data.get("categories", [])
    if not isinstance(categories, list):
        return jsonify({"error": "Categories must be a list"}), 400

    # Get the database connection to add tenant/team context
    db = get_db()
    review_id = db.reviews.insert(
        external_id=data.get("external_id"),
        platform=data.get("platform"),
        repository=data.get("repository"),
        pull_request_id=data.get("pull_request_id"),
        pull_request_url=data.get("pull_request_url"),
        base_sha=data.get("base_sha"),
        head_sha=data.get("head_sha"),
        review_type=data.get("review_type"),
        categories=categories,
        ai_provider=data.get("ai_provider"),
        status="queued",
        tenant_id=tenant_id,
        team_id=team_id,
        triggered_by=user_id,
    )
    db.commit()
    review = get_review_by_id(review_id)

    return jsonify(review), 201


@reviews_bp.route("/<int:review_id>", methods=["GET"])
@auth_required
def get_review(review_id: int):
    """Get a specific review by ID with tenant isolation."""
    review = get_review_by_id(review_id)

    if not review:
        return jsonify({"error": "Review not found"}), 404

    # Verify tenant isolation
    user = get_current_user()
    if not user:
        return jsonify({"error": "User context required"}), 401

    user_id = user.get("id")
    user_tenant_filter = get_user_tenant_filter(user_id)

    # Enforce tenant isolation - tenant users can only access their own tenant
    if user_tenant_filter is not None and review.get("tenant_id") != user_tenant_filter:
        return jsonify({
            "error": "Access denied - review does not belong to your tenant",
            "review_tenant_id": review.get("tenant_id"),
            "user_tenant_id": user_tenant_filter,
        }), 403

    # Enrich response with related data
    comments = get_comments_by_review(review_id)
    detections = get_detections_by_review(review_id)
    usage = get_usage_by_review(review_id)

    return jsonify({
        **review,
        "comments": comments,
        "detections": detections,
        "usage": usage,
    }), 200


@reviews_bp.route("", methods=["GET"])
@auth_required
def list_all_reviews():
    """List reviews with optional filtering and tenant isolation."""
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    platform = request.args.get("platform")
    repository = request.args.get("repository")
    status = request.args.get("status")

    # Validate pagination
    if page < 1:
        page = 1
    if per_page < 1 or per_page > 100:
        per_page = 20

    # Get current user for tenant filtering
    user = get_current_user()
    if not user:
        return jsonify({"error": "User context required"}), 401

    user_id = user.get("id")
    user_tenant_filter = get_user_tenant_filter(user_id)

    # Build query with tenant isolation
    db = get_db()
    offset = (page - 1) * per_page

    # Base query
    query = db.reviews.id > 0

    # Apply tenant filter - global users (None) see all, tenant users see only their tenant
    if user_tenant_filter is not None:
        query &= db.reviews.tenant_id == user_tenant_filter

    # Apply optional filters
    if platform:
        query &= db.reviews.platform == platform
    if repository:
        query &= db.reviews.repository == repository
    if status:
        query &= db.reviews.status == status

    # Execute query
    reviews = db(query).select(
        orderby=~db.reviews.created_at,
        limitby=(offset, offset + per_page),
    )
    total = db(query).count()

    return jsonify({
        "data": [r.as_dict() for r in reviews],
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": (total + per_page - 1) // per_page,
        },
    }), 200


@reviews_bp.route("/<int:review_id>/retry", methods=["POST"])
@auth_required
@role_required("admin", "maintainer")
def retry_review(review_id: int):
    """Retry a failed review with tenant isolation."""
    review = get_review_by_id(review_id)

    if not review:
        return jsonify({"error": "Review not found"}), 404

    # Verify tenant isolation
    user = get_current_user()
    if not user:
        return jsonify({"error": "User context required"}), 401

    user_id = user.get("id")
    user_tenant_filter = get_user_tenant_filter(user_id)

    # Enforce tenant isolation - tenant users can only retry reviews in their tenant
    if user_tenant_filter is not None and review.get("tenant_id") != user_tenant_filter:
        return jsonify({
            "error": "Access denied - review does not belong to your tenant",
            "review_tenant_id": review.get("tenant_id"),
            "user_tenant_id": user_tenant_filter,
        }), 403

    # Only allow retrying failed reviews
    if review.get("status") not in ["failed", "cancelled"]:
        return jsonify({
            "error": f"Cannot retry review with status '{review.get('status')}'",
            "allowed_statuses": ["failed", "cancelled"],
        }), 400

    # Reset review to queued status
    updated_review = update_review_status(review_id, "queued")

    return jsonify({
        "message": "Review queued for retry",
        "review": updated_review,
    }), 200


@reviews_bp.route("/<int:review_id>/cancel", methods=["POST"])
@auth_required
@role_required("admin", "maintainer")
def cancel_review(review_id: int):
    """Cancel an in-progress or queued review with tenant isolation."""
    review = get_review_by_id(review_id)

    if not review:
        return jsonify({"error": "Review not found"}), 404

    # Verify tenant isolation
    user = get_current_user()
    if not user:
        return jsonify({"error": "User context required"}), 401

    user_id = user.get("id")
    user_tenant_filter = get_user_tenant_filter(user_id)

    # Enforce tenant isolation - tenant users can only cancel reviews in their tenant
    if user_tenant_filter is not None and review.get("tenant_id") != user_tenant_filter:
        return jsonify({
            "error": "Access denied - review does not belong to your tenant",
            "review_tenant_id": review.get("tenant_id"),
            "user_tenant_id": user_tenant_filter,
        }), 403

    # Only allow cancelling queued or in-progress reviews
    if review.get("status") not in ["queued", "in_progress"]:
        return jsonify({
            "error": f"Cannot cancel review with status '{review.get('status')}'",
            "allowed_statuses": ["queued", "in_progress"],
        }), 400

    # Update review to cancelled
    updated_review = update_review_status(review_id, "cancelled")

    return jsonify({
        "message": "Review cancelled",
        "review": updated_review,
    }), 200


@reviews_bp.route("/external/<external_id>", methods=["GET"])
@auth_required
def get_review_by_external(external_id: str):
    """Get review by external ID (from GitHub/GitLab) with tenant isolation."""
    review = get_review_by_external_id(external_id)

    if not review:
        return jsonify({"error": "Review not found"}), 404

    # Verify tenant isolation
    user = get_current_user()
    if not user:
        return jsonify({"error": "User context required"}), 401

    user_id = user.get("id")
    user_tenant_filter = get_user_tenant_filter(user_id)

    # Enforce tenant isolation - tenant users can only access reviews in their tenant
    if user_tenant_filter is not None and review.get("tenant_id") != user_tenant_filter:
        return jsonify({
            "error": "Access denied - review does not belong to your tenant",
            "review_tenant_id": review.get("tenant_id"),
            "user_tenant_id": user_tenant_filter,
        }), 403

    # Enrich response with related data
    comments = get_comments_by_review(review.get("id"))
    detections = get_detections_by_review(review.get("id"))
    usage = get_usage_by_review(review.get("id"))

    return jsonify({
        **review,
        "comments": comments,
        "detections": detections,
        "usage": usage,
    }), 200


@reviews_bp.route("/<int:review_id>/status", methods=["PATCH"])
@auth_required
@role_required("admin", "maintainer")
def update_review(review_id: int):
    """Update review status and metrics with tenant isolation."""
    review = get_review_by_id(review_id)

    if not review:
        return jsonify({"error": "Review not found"}), 404

    # Verify tenant isolation
    user = get_current_user()
    if not user:
        return jsonify({"error": "User context required"}), 401

    user_id = user.get("id")
    user_tenant_filter = get_user_tenant_filter(user_id)

    # Enforce tenant isolation - tenant users can only update reviews in their tenant
    if user_tenant_filter is not None and review.get("tenant_id") != user_tenant_filter:
        return jsonify({
            "error": "Access denied - review does not belong to your tenant",
            "review_tenant_id": review.get("tenant_id"),
            "user_tenant_id": user_tenant_filter,
        }), 403

    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body required"}), 400

    # Validate status if provided
    new_status = data.get("status")
    if new_status:
        valid_statuses = ["queued", "in_progress", "completed", "failed", "cancelled"]
        if new_status not in valid_statuses:
            return jsonify({
                "error": f"Invalid status: {new_status}",
                "valid_statuses": valid_statuses,
            }), 400

    # Update review
    updated_review = update_review_status(
        review_id,
        new_status or review.get("status"),
        error_message=data.get("error_message"),
        files_reviewed=data.get("files_reviewed"),
        comments_posted=data.get("comments_posted"),
    )

    return jsonify(updated_review), 200


@reviews_bp.route("/<int:review_id>/comments", methods=["GET"])
@auth_required
def get_review_comments(review_id: int):
    """Get all comments for a review with tenant isolation."""
    review = get_review_by_id(review_id)

    if not review:
        return jsonify({"error": "Review not found"}), 404

    # Verify tenant isolation
    user = get_current_user()
    if not user:
        return jsonify({"error": "User context required"}), 401

    user_id = user.get("id")
    user_tenant_filter = get_user_tenant_filter(user_id)

    # Enforce tenant isolation - tenant users can only access comments in their tenant
    if user_tenant_filter is not None and review.get("tenant_id") != user_tenant_filter:
        return jsonify({
            "error": "Access denied - review does not belong to your tenant",
            "review_tenant_id": review.get("tenant_id"),
            "user_tenant_id": user_tenant_filter,
        }), 403

    category = request.args.get("category")
    severity = request.args.get("severity")

    comments = get_comments_by_review(
        review_id,
        category=category,
        severity=severity,
    )

    return jsonify({
        "review_id": review_id,
        "total": len(comments),
        "comments": comments,
    }), 200

"""
G5–G11: Full GenAI Tool Layer
Every tool receives org_id + user_role from the authenticated backend user.
The LLM never queries the database directly.
"""

import json
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import Dict, Any, Optional

from backend.app.models.store import Store
from backend.app.models.audit import ShelfAudit, AuditStatus
from backend.app.models.compliance import ComplianceResult, ComplianceViolation, ViolationType
from backend.app.models.review import HumanReview, MLTrainingSample, ReviewStatus, StorageStatus, SampleStatus
from backend.app.models.ml import ModelVersion, ModelStatus, Recognition, RecognitionStatus, Detection, ActualShelfPosition
from backend.app.models.planogram import Planogram, PlanogramVersion, PlanogramVersionStatus, PlanogramPosition
from backend.app.models.product import Product

# ─────────────────────────────────────────────
#  ROLE CONSTANTS
# ─────────────────────────────────────────────
MANAGER_ROLES = {"MANAGER", "ADMIN"}
EMPLOYEE_ROLES = {"EMPLOYEE", "ADMIN"}

# ─────────────────────────────────────────────
#  ALLOWED NAVIGATION ROUTES
# ─────────────────────────────────────────────
MANAGER_ROUTES = [
    "/manager", "/manager/stores", "/manager/products",
    "/manager/planograms", "/manager/audits", "/manager/reviews",
    "/manager/employees",
]
EMPLOYEE_ROUTES = [
    "/employee", "/employee/audit/new",
]

# ─────────────────────────────────────────────
#  TOOL DEFINITIONS (OpenAI function-calling format)
# ─────────────────────────────────────────────
TOOLS = [
    # ── G6: Core data tools ──
    {
        "type": "function",
        "function": {
            "name": "get_store_compliance_overview",
            "description": "Get a snapshot of every store's latest compliance score. Use when asked about store performance or compliance comparisons.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_audit_summary",
            "description": "Get a detailed summary of a specific audit including compliance metrics, violation breakdown by shelf and position, and pending review count. Use when asked to explain or summarize a specific audit.",
            "parameters": {
                "type": "object",
                "properties": {
                    "audit_id": {
                        "type": "string",
                        "description": "The UUID of the audit. If omitted, uses the current page context."
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_latest_audit",
            "description": "Get the most recently completed audit for the organization. Use when the user says 'my latest audit' or 'last audit'.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_pending_reviews",
            "description": "Get a summary of pending human reviews for ML recognition corrections. Manager-only.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_review_detail",
            "description": "Get full details of a specific human review item, including why it was flagged, predicted SKU, similarity score, margin, and threshold. Manager-only.",
            "parameters": {
                "type": "object",
                "properties": {
                    "review_id": {
                        "type": "string",
                        "description": "The UUID of the human review."
                    }
                },
                "required": ["review_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_model_status",
            "description": "Get the status of the active ML recognition model, training queue, pending samples, and lifecycle state. Manager-only.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_planogram_status",
            "description": "Get a summary of all planograms and their versions for the organization. Manager-only.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_product_summary",
            "description": "Get a summary of the product master for the organization. Manager-only.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    # ── G7: Analytics tools ──
    {
        "type": "function",
        "function": {
            "name": "get_audit_statistics",
            "description": "Get aggregated audit statistics: total audits, audits by status, audits this week/month, average compliance. Manager-only.",
            "parameters": {
                "type": "object",
                "properties": {
                    "days": {
                        "type": "integer",
                        "description": "Number of days to look back. Default 30."
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_violation_analytics",
            "description": "Get aggregated violation analytics: most common violation type, violations by store, violations by product. Manager-only.",
            "parameters": {
                "type": "object",
                "properties": {
                    "days": {
                        "type": "integer",
                        "description": "Number of days to look back. Default 30."
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_compliance_trend",
            "description": "Get compliance trend over time (average compliance per week). Manager-only.",
            "parameters": {
                "type": "object",
                "properties": {
                    "weeks": {
                        "type": "integer",
                        "description": "Number of weeks to look back. Default 8."
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_pending_review_statistics",
            "description": "Get statistics about pending human reviews: total, by storage status, average similarity score. Manager-only.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    # ── G8: Navigation ──
    {
        "type": "function",
        "function": {
            "name": "navigate_to_page",
            "description": "Navigate the user's browser to a specific page in the application. Always validate the route against the user's role.",
            "parameters": {
                "type": "object",
                "properties": {
                    "route": {
                        "type": "string",
                        "description": "The frontend route to navigate to."
                    }
                },
                "required": ["route"]
            }
        }
    },
    # ── G9: Explain Audit ──
    {
        "type": "function",
        "function": {
            "name": "explain_audit",
            "description": "Get a comprehensive, grounded explanation of a specific audit: compliance scores, each violation with shelf/position/product details, and actionable recommendations. Use when the user clicks 'Explain This Audit' or asks 'what happened in this audit'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "audit_id": {
                        "type": "string",
                        "description": "The UUID of the audit to explain."
                    }
                },
                "required": []
            }
        }
    },
    # ── G10: Review Copilot ──
    {
        "type": "function",
        "function": {
            "name": "explain_review",
            "description": "Explain why a specific product was sent for human review: predicted SKU, similarity score, review threshold, margin. Manager-only.",
            "parameters": {
                "type": "object",
                "properties": {
                    "review_id": {
                        "type": "string",
                        "description": "The UUID of the human review to explain."
                    }
                },
                "required": []
            }
        }
    },
    # ── G11: ML Lifecycle ──
    {
        "type": "function",
        "function": {
            "name": "get_ml_lifecycle_status",
            "description": "Get a full overview of the ML model lifecycle: active model, training status, sample counts by storage status, retraining thresholds, last training date, and pipeline health. Manager-only.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    # ── Documentation search ──
    {
        "type": "function",
        "function": {
            "name": "search_application_documentation",
            "description": "Search the internal knowledge base for how the application works.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The topic to search for."
                    }
                },
                "required": ["query"]
            }
        }
    }
]

# ─────────────────────────────────────────────
#  HELPER: Role gate
# ─────────────────────────────────────────────
def _require_manager(user_role: str) -> Optional[Dict]:
    """Returns an error dict if the user is not a manager. Returns None if OK."""
    roles = set(r.strip().upper() for r in user_role.split(","))
    if not roles.intersection(MANAGER_ROLES):
        return {"error": "This information is only available to managers. As an employee, you can view your own audits and start new ones."}
    return None

# ─────────────────────────────────────────────
#  G6: Core Data Tools
# ─────────────────────────────────────────────
def get_store_compliance_overview(db: Session, org_id: str, user_role: str) -> Dict[str, Any]:
    stores = db.query(Store).filter(Store.organization_id == org_id).all()
    results = []
    for s in stores:
        latest_audit = db.query(ShelfAudit).filter(
            ShelfAudit.store_id == s.id,
            ShelfAudit.organization_id == org_id,
            ShelfAudit.status == AuditStatus.COMPLETED
        ).order_by(ShelfAudit.created_at.desc()).first()

        comp_score = None
        audit_date = None
        if latest_audit:
            comp_result = db.query(ComplianceResult).filter(ComplianceResult.audit_id == latest_audit.id).first()
            if comp_result:
                comp_score = round(comp_result.availability_rate * 100, 1)
            audit_date = latest_audit.created_at.isoformat() if latest_audit.created_at else None

        results.append({
            "store_name": s.name,
            "latest_compliance_percent": comp_score,
            "last_audit_date": audit_date
        })
    return {"stores": results}


def get_latest_audit(db: Session, org_id: str, user_role: str) -> Dict[str, Any]:
    latest = db.query(ShelfAudit).filter(
        ShelfAudit.organization_id == org_id,
        ShelfAudit.status == AuditStatus.COMPLETED
    ).order_by(ShelfAudit.created_at.desc()).first()

    if not latest:
        return {"error": "No completed audits found."}

    return get_audit_summary(db, org_id, user_role, str(latest.id))


def get_audit_summary(db: Session, org_id: str, user_role: str, audit_id: str) -> Dict[str, Any]:
    audit = db.query(ShelfAudit).filter(ShelfAudit.id == audit_id, ShelfAudit.organization_id == org_id).first()
    if not audit:
        return {"error": "Audit not found."}

    comp_result = db.query(ComplianceResult).filter(ComplianceResult.audit_id == audit.id).first()
    violations = db.query(ComplianceViolation).filter(ComplianceViolation.audit_id == audit.id).all()

    # Build violation details with product names
    violation_details = []
    for v in violations:
        exp_product = db.query(Product).filter(Product.id == v.expected_product_id).first() if v.expected_product_id else None
        act_product = db.query(Product).filter(Product.id == v.actual_product_id).first() if v.actual_product_id else None
        violation_details.append({
            "type": v.violation_type.value,
            "shelf": v.shelf_id,
            "position": v.position,
            "expected_product": exp_product.name if exp_product else None,
            "expected_sku": exp_product.sku_code if exp_product else None,
            "actual_product": act_product.name if act_product else None,
            "actual_sku": act_product.sku_code if act_product else None,
        })

    missing = sum(1 for v in violations if v.violation_type == ViolationType.MISSING_PRODUCT)
    misplaced = sum(1 for v in violations if v.violation_type == ViolationType.MISPLACED_PRODUCT)
    extra = sum(1 for v in violations if v.violation_type == ViolationType.EXTRA_PRODUCT)
    facing = sum(1 for v in violations if v.violation_type == ViolationType.FACING_MISMATCH)

    pending_reviews = db.query(HumanReview).filter(
        HumanReview.audit_id == audit.id,
        HumanReview.status == ReviewStatus.PENDING,
        HumanReview.organization_id == org_id
    ).count()

    # Get store and planogram names
    store = db.query(Store).filter(Store.id == audit.store_id).first()
    from backend.app.models.planogram import PlanogramVersion as PV, Planogram as PG
    pv = db.query(PV).filter(PV.id == audit.planogram_version_id).first()
    pg = db.query(PG).filter(PG.id == pv.planogram_id).first() if pv else None

    return {
        "audit_id": str(audit.id),
        "store_name": store.name if store else "Unknown",
        "planogram_name": pg.name if pg else "Unknown",
        "status": audit.status.value,
        "created_at": audit.created_at.isoformat() if audit.created_at else None,
        "compliance": {
            "availability_rate_percent": round(comp_result.availability_rate * 100, 1) if comp_result else None,
            "position_accuracy_percent": round(comp_result.position_accuracy * 100, 1) if comp_result else None,
            "facing_compliance_percent": round(comp_result.facing_compliance * 100, 1) if comp_result else None,
        },
        "violation_counts": {
            "missing": missing,
            "misplaced": misplaced,
            "extra": extra,
            "facing_mismatch": facing,
            "total": missing + misplaced + extra + facing
        },
        "violation_details": violation_details,
        "pending_human_reviews": pending_reviews,
        "definitions": {
            "MISSING_PRODUCT": "A product expected by the planogram was not detected on the shelf.",
            "EXTRA_PRODUCT": "A product was detected on the shelf that was not expected by the planogram.",
            "MISPLACED_PRODUCT": "A product was detected at a different shelf/position than where the planogram expects it.",
            "FACING_MISMATCH": "The number of facings (visible units) of a product differs from what the planogram expects. This does NOT mean the product is facing the wrong direction."
        }
    }


def get_pending_reviews(db: Session, org_id: str, user_role: str) -> Dict[str, Any]:
    gate = _require_manager(user_role)
    if gate:
        return gate

    pending = db.query(HumanReview).filter(
        HumanReview.organization_id == org_id,
        HumanReview.status == ReviewStatus.PENDING
    ).all()

    items = []
    for r in pending:
        predicted = db.query(Product).filter(Product.id == r.predicted_product_id).first() if r.predicted_product_id else None
        items.append({
            "review_id": str(r.id),
            "audit_id": str(r.audit_id),
            "predicted_product": predicted.name if predicted else "Unknown",
            "predicted_sku": predicted.sku_code if predicted else "N/A",
            "similarity": round(r.predicted_similarity, 3) if r.predicted_similarity else None,
            "margin": round(r.predicted_margin, 3) if r.predicted_margin else None,
        })

    return {"total_pending": len(items), "reviews": items[:20]}  # Cap at 20 for LLM context


def get_review_detail(db: Session, org_id: str, user_role: str, review_id: str) -> Dict[str, Any]:
    gate = _require_manager(user_role)
    if gate:
        return gate

    review = db.query(HumanReview).filter(
        HumanReview.id == review_id,
        HumanReview.organization_id == org_id
    ).first()
    if not review:
        return {"error": "Review not found."}

    from backend.app.core.config import settings

    predicted = db.query(Product).filter(Product.id == review.predicted_product_id).first() if review.predicted_product_id else None
    corrected = db.query(Product).filter(Product.id == review.corrected_product_id).first() if review.corrected_product_id else None

    return {
        "review_id": str(review.id),
        "audit_id": str(review.audit_id),
        "status": review.status.value,
        "predicted_product": predicted.name if predicted else "Unknown",
        "predicted_sku": predicted.sku_code if predicted else "N/A",
        "similarity": round(review.predicted_similarity, 3) if review.predicted_similarity else None,
        "margin": round(review.predicted_margin, 3) if review.predicted_margin else None,
        "review_threshold": settings.RECOGNITION_REVIEW_THRESHOLD,
        "corrected_product": corrected.name if corrected else None,
        "corrected_sku": corrected.sku_code if corrected else None,
        "reviewed_at": review.reviewed_at.isoformat() if review.reviewed_at else None,
        "reason_for_review": f"The recognition similarity of {round(review.predicted_similarity, 3) if review.predicted_similarity else 'N/A'} is below the review threshold of {settings.RECOGNITION_REVIEW_THRESHOLD}."
    }


def get_model_status(db: Session, org_id: str, user_role: str) -> Dict[str, Any]:
    gate = _require_manager(user_role)
    if gate:
        return gate

    active_model = db.query(ModelVersion).filter(
        ModelVersion.status == ModelStatus.ACTIVE
    ).order_by(ModelVersion.created_at.desc()).first()

    training_model = db.query(ModelVersion).filter(
        ModelVersion.status == ModelStatus.TRAINING
    ).first()

    candidate_model = db.query(ModelVersion).filter(
        ModelVersion.status == ModelStatus.CANDIDATE
    ).first()

    from backend.app.core.config import settings

    pending_samples = db.query(MLTrainingSample).filter(
        MLTrainingSample.organization_id == org_id,
        MLTrainingSample.status == SampleStatus.PENDING
    ).count()

    available_samples = db.query(MLTrainingSample).filter(
        MLTrainingSample.organization_id == org_id,
        MLTrainingSample.status == SampleStatus.PENDING,
        MLTrainingSample.storage_status == StorageStatus.AVAILABLE
    ).count()

    return {
        "active_model_version": active_model.version if active_model else "v1_baseline",
        "active_model_name": active_model.model_name if active_model else "baseline",
        "pipeline_status": "TRAINING" if training_model else ("CANDIDATE_READY" if candidate_model else "IDLE"),
        "candidate_model": candidate_model.version if candidate_model else None,
        "total_pending_samples": pending_samples,
        "samples_uploaded_to_s3": available_samples,
        "required_for_training": settings.MIN_NEW_TRAINING_SAMPLES,
        "ready_to_train": available_samples >= settings.MIN_NEW_TRAINING_SAMPLES,
        "last_training_date": active_model.created_at.isoformat() if active_model else "Never"
    }


def get_planogram_status(db: Session, org_id: str, user_role: str) -> Dict[str, Any]:
    gate = _require_manager(user_role)
    if gate:
        return gate

    planograms = db.query(Planogram).filter(Planogram.organization_id == org_id).all()
    items = []
    for p in planograms:
        versions = db.query(PlanogramVersion).filter(PlanogramVersion.planogram_id == p.id).all()
        store = db.query(Store).filter(Store.id == p.store_id).first() if p.store_id else None
        items.append({
            "name": p.name,
            "code": p.code,
            "store": store.name if store else "Unassigned",
            "status": p.status.value,
            "version_count": len(versions),
            "latest_version": max(v.version_number for v in versions) if versions else 0,
        })
    return {"total_planograms": len(items), "planograms": items}


def get_product_summary(db: Session, org_id: str, user_role: str) -> Dict[str, Any]:
    gate = _require_manager(user_role)
    if gate:
        return gate

    products = db.query(Product).filter(Product.organization_id == org_id).all()
    brands = {}
    for p in products:
        brand = p.brand or "Unknown"
        brands[brand] = brands.get(brand, 0) + 1

    return {
        "total_products": len(products),
        "brands": [{"brand": k, "count": v} for k, v in sorted(brands.items(), key=lambda x: -x[1])],
        "sample_products": [{"name": p.name, "sku": p.sku_code, "brand": p.brand} for p in products[:10]]
    }


# ─────────────────────────────────────────────
#  G7: Analytics Tools
# ─────────────────────────────────────────────
def get_audit_statistics(db: Session, org_id: str, user_role: str, days: int = 30) -> Dict[str, Any]:
    gate = _require_manager(user_role)
    if gate:
        return gate

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    total = db.query(ShelfAudit).filter(ShelfAudit.organization_id == org_id).count()
    recent = db.query(ShelfAudit).filter(
        ShelfAudit.organization_id == org_id,
        ShelfAudit.created_at >= cutoff
    ).all()

    by_status = {}
    for a in recent:
        s = a.status.value
        by_status[s] = by_status.get(s, 0) + 1

    # Average compliance for recent completed audits
    recent_completed_ids = [a.id for a in recent if a.status == AuditStatus.COMPLETED]
    avg_compliance = None
    if recent_completed_ids:
        avg = db.query(func.avg(ComplianceResult.availability_rate)).filter(
            ComplianceResult.audit_id.in_(recent_completed_ids)
        ).scalar()
        if avg is not None:
            avg_compliance = round(float(avg) * 100, 1)

    # This week
    week_start = datetime.now(timezone.utc) - timedelta(days=datetime.now(timezone.utc).weekday())
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
    this_week = db.query(ShelfAudit).filter(
        ShelfAudit.organization_id == org_id,
        ShelfAudit.created_at >= week_start
    ).count()

    return {
        "period_days": days,
        "total_all_time": total,
        "total_in_period": len(recent),
        "this_week": this_week,
        "by_status": by_status,
        "average_compliance_percent": avg_compliance
    }


def get_violation_analytics(db: Session, org_id: str, user_role: str, days: int = 30) -> Dict[str, Any]:
    gate = _require_manager(user_role)
    if gate:
        return gate

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    # Get recent audit IDs
    recent_audits = db.query(ShelfAudit.id).filter(
        ShelfAudit.organization_id == org_id,
        ShelfAudit.created_at >= cutoff
    ).all()
    recent_ids = [a.id for a in recent_audits]

    if not recent_ids:
        return {"period_days": days, "total_violations": 0, "message": "No audits in this period."}

    # By type
    type_counts = db.query(
        ComplianceViolation.violation_type, func.count()
    ).filter(
        ComplianceViolation.audit_id.in_(recent_ids)
    ).group_by(ComplianceViolation.violation_type).all()

    by_type = {t.value: c for t, c in type_counts}
    total_violations = sum(by_type.values())

    # By store (top 5 most violations)
    store_violations = db.query(
        Store.name, func.count(ComplianceViolation.id)
    ).join(
        ShelfAudit, ShelfAudit.store_id == Store.id
    ).join(
        ComplianceViolation, ComplianceViolation.audit_id == ShelfAudit.id
    ).filter(
        ShelfAudit.organization_id == org_id,
        ShelfAudit.created_at >= cutoff
    ).group_by(Store.name).order_by(func.count(ComplianceViolation.id).desc()).limit(5).all()

    # Most problematic products (top 5)
    problem_products = db.query(
        Product.name, Product.sku_code, func.count(ComplianceViolation.id)
    ).join(
        ComplianceViolation, ComplianceViolation.expected_product_id == Product.id
    ).join(
        ShelfAudit, ShelfAudit.id == ComplianceViolation.audit_id
    ).filter(
        ShelfAudit.organization_id == org_id,
        ShelfAudit.created_at >= cutoff
    ).group_by(Product.name, Product.sku_code).order_by(func.count(ComplianceViolation.id).desc()).limit(5).all()

    return {
        "period_days": days,
        "total_violations": total_violations,
        "by_type": by_type,
        "most_common_type": max(by_type, key=by_type.get) if by_type else None,
        "by_store": [{"store": name, "violations": count} for name, count in store_violations],
        "most_problematic_products": [{"product": name, "sku": sku, "violations": count} for name, sku, count in problem_products]
    }


def get_compliance_trend(db: Session, org_id: str, user_role: str, weeks: int = 8) -> Dict[str, Any]:
    gate = _require_manager(user_role)
    if gate:
        return gate

    trend = []
    now = datetime.now(timezone.utc)
    for i in range(weeks - 1, -1, -1):
        week_start = now - timedelta(weeks=i + 1)
        week_end = now - timedelta(weeks=i)

        audit_ids = db.query(ShelfAudit.id).filter(
            ShelfAudit.organization_id == org_id,
            ShelfAudit.status == AuditStatus.COMPLETED,
            ShelfAudit.created_at >= week_start,
            ShelfAudit.created_at < week_end
        ).all()

        avg = None
        if audit_ids:
            ids = [a.id for a in audit_ids]
            result = db.query(func.avg(ComplianceResult.availability_rate)).filter(
                ComplianceResult.audit_id.in_(ids)
            ).scalar()
            if result is not None:
                avg = round(float(result) * 100, 1)

        trend.append({
            "week_ending": week_end.strftime("%Y-%m-%d"),
            "audits_count": len(audit_ids),
            "average_compliance_percent": avg
        })

    return {"weeks": weeks, "trend": trend}


def get_pending_review_statistics(db: Session, org_id: str, user_role: str) -> Dict[str, Any]:
    gate = _require_manager(user_role)
    if gate:
        return gate

    total_pending = db.query(HumanReview).filter(
        HumanReview.organization_id == org_id,
        HumanReview.status == ReviewStatus.PENDING
    ).count()

    total_completed = db.query(HumanReview).filter(
        HumanReview.organization_id == org_id,
        HumanReview.status == ReviewStatus.COMPLETED
    ).count()

    avg_similarity = db.query(func.avg(HumanReview.predicted_similarity)).filter(
        HumanReview.organization_id == org_id,
        HumanReview.status == ReviewStatus.PENDING
    ).scalar()

    return {
        "total_pending": total_pending,
        "total_completed": total_completed,
        "average_similarity_of_pending": round(float(avg_similarity), 3) if avg_similarity else None,
    }


# ─────────────────────────────────────────────
#  G8: Navigation
# ─────────────────────────────────────────────

# Route aliases: maps LLM guesses / sidebar labels to real React routes.
# Sidebar shows "Staff" but route is /manager/employees — this bridges that gap.
ROUTE_ALIASES: Dict[str, str] = {
    # "Staff" in the sidebar = /manager/employees
    "/manager/staff":          "/manager/employees",
    "/manager/team":           "/manager/employees",
    "/manager/users":          "/manager/employees",
    "/manager/members":        "/manager/employees",
    # Singular shorthand
    "/manager/audit":          "/manager/audits",
    "/manager/review":         "/manager/reviews",
    "/manager/product":        "/manager/products",
    "/manager/product-master": "/manager/products",
    "/manager/planogram":      "/manager/planograms",
    "/manager/store":          "/manager/stores",
    # Employee side
    "/employee/audit":         "/employee/audit/new",
}

def navigate_to_page(user_role: str, route: str) -> Dict[str, Any]:
    roles = set(r.strip().upper() for r in user_role.split(","))

    # Step 1: Resolve alias BEFORE validation.
    # e.g. /manager/staff → /manager/employees  (sidebar label vs actual route)
    #      /manager/audit → /manager/audits
    canonical_route = ROUTE_ALIASES.get(route, route)

    # Step 2: Validate canonical route against role + allowlist
    if canonical_route.startswith("/manager"):
        if not roles.intersection(MANAGER_ROLES):
            return {"error": "You do not have access to manager pages."}
        if not any(canonical_route == r or canonical_route.startswith(r + "/") for r in MANAGER_ROUTES):
            return {"error": f"Route '{route}' is not a recognized manager page."}
    elif canonical_route.startswith("/employee"):
        if not roles.intersection(EMPLOYEE_ROLES):
            return {"error": "You do not have access to employee pages."}
        if not any(canonical_route == r or canonical_route.startswith(r + "/") for r in EMPLOYEE_ROUTES):
            return {"error": f"Route '{route}' is not a recognized employee page."}
    else:
        return {"error": f"Navigation to '{route}' is not allowed."}

    # Step 3: Always return canonical_route so the frontend navigates to the REAL path
    return {"action": "NAVIGATE", "route": canonical_route}


# ─────────────────────────────────────────────
#  G9: Explain Audit (deep, grounded)
# ─────────────────────────────────────────────
def explain_audit(db: Session, org_id: str, user_role: str, audit_id: str) -> Dict[str, Any]:
    # Reuse get_audit_summary for the base data
    summary = get_audit_summary(db, org_id, user_role, audit_id)
    if "error" in summary:
        return summary

    # Group violations by shelf for a structured explanation
    shelves = {}
    for v in summary.get("violation_details", []):
        sid = v["shelf"]
        if sid not in shelves:
            shelves[sid] = []
        shelves[sid].append(v)

    summary["violations_by_shelf"] = {
        f"Shelf {sid}": violations for sid, violations in sorted(shelves.items())
    }

    summary["explanation_guidance"] = (
        "Use the violation_details and violations_by_shelf data to give the user a clear, "
        "shelf-by-shelf explanation. For each violation, reference the exact shelf number, "
        "position number, product name, and violation type. Use the definitions provided. "
        "End with actionable recommendations: which products to fix first (missing > misplaced > facing)."
    )

    return summary


# ─────────────────────────────────────────────
#  G10: Review Copilot
# ─────────────────────────────────────────────
def explain_review(db: Session, org_id: str, user_role: str, review_id: str) -> Dict[str, Any]:
    gate = _require_manager(user_role)
    if gate:
        return gate

    detail = get_review_detail(db, org_id, user_role, review_id)
    if "error" in detail:
        return detail

    detail["explanation_guidance"] = (
        "Explain to the manager: 1) Why this item was flagged (similarity vs threshold), "
        "2) What the model predicted, 3) What the manager's options are: "
        "a) Select an existing Product/SKU if the model was wrong, "
        "b) Select 'Others / New Product' if this is a new product not in the system. "
        "Do NOT autonomously change any data. This is read/explain only."
    )

    return detail


# ─────────────────────────────────────────────
#  G11: ML Lifecycle
# ─────────────────────────────────────────────
def get_ml_lifecycle_status(db: Session, org_id: str, user_role: str) -> Dict[str, Any]:
    gate = _require_manager(user_role)
    if gate:
        return gate

    from backend.app.core.config import settings

    # Active model
    active = db.query(ModelVersion).filter(ModelVersion.status == ModelStatus.ACTIVE).order_by(ModelVersion.created_at.desc()).first()
    training = db.query(ModelVersion).filter(ModelVersion.status == ModelStatus.TRAINING).first()
    candidate = db.query(ModelVersion).filter(ModelVersion.status == ModelStatus.CANDIDATE).first()

    # Sample breakdown
    total_samples = db.query(MLTrainingSample).filter(MLTrainingSample.organization_id == org_id).count()
    pending = db.query(MLTrainingSample).filter(MLTrainingSample.organization_id == org_id, MLTrainingSample.status == SampleStatus.PENDING).count()
    available_on_s3 = db.query(MLTrainingSample).filter(
        MLTrainingSample.organization_id == org_id,
        MLTrainingSample.status == SampleStatus.PENDING,
        MLTrainingSample.storage_status == StorageStatus.AVAILABLE
    ).count()
    failed_upload = db.query(MLTrainingSample).filter(
        MLTrainingSample.organization_id == org_id,
        MLTrainingSample.storage_status.in_([StorageStatus.FAILED_RETRYABLE, StorageStatus.FAILED_PERMANENT])
    ).count()
    used = db.query(MLTrainingSample).filter(MLTrainingSample.organization_id == org_id, MLTrainingSample.status == SampleStatus.USED_FOR_TRAINING).count()

    # Review → Sample pipeline
    total_reviews = db.query(HumanReview).filter(HumanReview.organization_id == org_id).count()
    completed_reviews = db.query(HumanReview).filter(HumanReview.organization_id == org_id, HumanReview.status == ReviewStatus.COMPLETED).count()
    pending_reviews = db.query(HumanReview).filter(HumanReview.organization_id == org_id, HumanReview.status == ReviewStatus.PENDING).count()

    return {
        "pipeline": {
            "step_1": "YOLO detection → finds product bounding boxes on the shelf image",
            "step_2": "ResNet recognition → identifies each product by comparing to reference embeddings",
            "step_3": f"Similarity check → if similarity < {settings.RECOGNITION_REVIEW_THRESHOLD}, item is sent for Human Review",
            "step_4": "Human Review → manager corrects the prediction → creates a Training Sample",
            "step_5": f"Training trigger → when {settings.MIN_NEW_TRAINING_SAMPLES} AVAILABLE samples exist on S3, retraining starts",
            "step_6": "Training → produces a Candidate model → evaluated → if good, promoted to Active"
        },
        "active_model": {
            "version": active.version if active else "v1_baseline",
            "model_name": active.model_name if active else "baseline",
            "created_at": active.created_at.isoformat() if active else "Never",
        },
        "training_status": {
            "currently_training": training is not None,
            "training_model": training.version if training else None,
            "candidate_ready": candidate is not None,
            "candidate_version": candidate.version if candidate else None,
        },
        "samples": {
            "total": total_samples,
            "pending_for_training": pending,
            "uploaded_to_s3": available_on_s3,
            "failed_upload": failed_upload,
            "already_used": used,
            "required_for_training": settings.MIN_NEW_TRAINING_SAMPLES,
            "ready_to_train": available_on_s3 >= settings.MIN_NEW_TRAINING_SAMPLES,
        },
        "reviews": {
            "total": total_reviews,
            "completed": completed_reviews,
            "pending": pending_reviews,
        },
        "thresholds": {
            "review_threshold": settings.RECOGNITION_REVIEW_THRESHOLD,
            "min_training_samples": settings.MIN_NEW_TRAINING_SAMPLES,
            "training_epochs": settings.TRAINING_EPOCHS,
            "evaluation_loss_threshold": settings.TRAINING_EVALUATION_LOSS_THRESHOLD,
        }
    }


# ─────────────────────────────────────────────
#  Documentation search
# ─────────────────────────────────────────────
def search_application_documentation(query: str) -> Dict[str, Any]:
    from backend.app.ai_rag.retriever import retrieve_context
    return {"documentation": retrieve_context(query)}


# ─────────────────────────────────────────────
#  DISPATCHER
# ─────────────────────────────────────────────
def execute_tool(tool_name: str, arguments: Dict[str, Any], db: Session, org_id: str, user_role: str, ctx: Any = None) -> Dict[str, Any]:
    """
    Central dispatcher. Every tool receives org_id and user_role from
    the authenticated backend user (NOT from the frontend request).
    """
    try:
        if tool_name == "get_store_compliance_overview":
            return get_store_compliance_overview(db, org_id, user_role)

        elif tool_name == "get_audit_summary":
            audit_id = arguments.get("audit_id")
            if not audit_id and ctx and getattr(ctx, "audit_id", None):
                audit_id = ctx.audit_id
            if not audit_id:
                return {"error": "No audit_id provided. Please specify which audit you are asking about."}
            return get_audit_summary(db, org_id, user_role, audit_id)

        elif tool_name == "get_latest_audit":
            return get_latest_audit(db, org_id, user_role)

        elif tool_name == "get_pending_reviews":
            return get_pending_reviews(db, org_id, user_role)

        elif tool_name == "get_review_detail":
            review_id = arguments.get("review_id")
            if not review_id and ctx and getattr(ctx, "review_id", None):
                review_id = ctx.review_id
            if not review_id:
                return {"error": "No review_id provided."}
            return get_review_detail(db, org_id, user_role, review_id)

        elif tool_name == "get_model_status":
            return get_model_status(db, org_id, user_role)

        elif tool_name == "get_planogram_status":
            return get_planogram_status(db, org_id, user_role)

        elif tool_name == "get_product_summary":
            return get_product_summary(db, org_id, user_role)

        elif tool_name == "get_audit_statistics":
            return get_audit_statistics(db, org_id, user_role, arguments.get("days", 30))

        elif tool_name == "get_violation_analytics":
            return get_violation_analytics(db, org_id, user_role, arguments.get("days", 30))

        elif tool_name == "get_compliance_trend":
            return get_compliance_trend(db, org_id, user_role, arguments.get("weeks", 8))

        elif tool_name == "get_pending_review_statistics":
            return get_pending_review_statistics(db, org_id, user_role)

        elif tool_name == "navigate_to_page":
            return navigate_to_page(user_role, arguments.get("route", ""))

        elif tool_name == "explain_audit":
            audit_id = arguments.get("audit_id")
            if not audit_id and ctx and getattr(ctx, "audit_id", None):
                audit_id = ctx.audit_id
            if not audit_id:
                return {"error": "No audit_id provided."}
            return explain_audit(db, org_id, user_role, audit_id)

        elif tool_name == "explain_review":
            review_id = arguments.get("review_id")
            if not review_id and ctx and getattr(ctx, "review_id", None):
                review_id = ctx.review_id
            if not review_id:
                return {"error": "No review_id provided."}
            return explain_review(db, org_id, user_role, review_id)

        elif tool_name == "get_ml_lifecycle_status":
            return get_ml_lifecycle_status(db, org_id, user_role)

        elif tool_name == "search_application_documentation":
            return search_application_documentation(arguments.get("query", ""))

        # Legacy aliases
        elif tool_name == "get_store_compliance_trends":
            return get_store_compliance_overview(db, org_id, user_role)

        else:
            return {"error": f"Unknown tool: {tool_name}"}

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": f"Tool execution failed: {str(e)}"}

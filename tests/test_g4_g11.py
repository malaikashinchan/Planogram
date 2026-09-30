"""
G4–G11 Comprehensive Test Suite
Tests every tool function, role gate, data accuracy, and RAG retrieval.
"""

import sys
import json
import traceback
from uuid import UUID
from datetime import datetime, timezone

from backend.app.core.database import SessionLocal
from backend.app.api.v1.ai_tools import (
    execute_tool, _require_manager, TOOLS,
    get_store_compliance_overview, get_audit_summary, get_latest_audit,
    get_pending_reviews, get_review_detail, get_model_status,
    get_planogram_status, get_product_summary,
    get_audit_statistics, get_violation_analytics, get_compliance_trend,
    get_pending_review_statistics, navigate_to_page,
    explain_audit, explain_review, get_ml_lifecycle_status,
    search_application_documentation,
)

# ─────────────────────────────────────────
#  Test infrastructure
# ─────────────────────────────────────────
PASS = 0
FAIL = 0
RESULTS = []

def test(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        RESULTS.append(("PASS", name, detail))
    else:
        FAIL += 1
        RESULTS.append(("FAIL", name, detail))

def section(title):
    RESULTS.append(("SECTION", title, ""))

# ─────────────────────────────────────────
#  Setup
# ─────────────────────────────────────────
db = SessionLocal()

# Get a real org_id from the database
from backend.app.models.user import User
from backend.app.models.audit import ShelfAudit, AuditStatus
from backend.app.models.compliance import ComplianceResult, ComplianceViolation
from backend.app.models.review import HumanReview, ReviewStatus, MLTrainingSample
from backend.app.models.store import Store

first_user = db.query(User).first()
ORG_ID = str(first_user.organization_id) if first_user else None

# Get a real audit ID
real_audit = db.query(ShelfAudit).filter(
    ShelfAudit.organization_id == ORG_ID,
    ShelfAudit.status == AuditStatus.COMPLETED
).order_by(ShelfAudit.created_at.desc()).first()
REAL_AUDIT_ID = str(real_audit.id) if real_audit else None

# Get a real review ID
real_review = db.query(HumanReview).filter(HumanReview.organization_id == ORG_ID).first()
REAL_REVIEW_ID = str(real_review.id) if real_review else None

print(f"Test setup: ORG_ID={ORG_ID}, AUDIT_ID={REAL_AUDIT_ID}, REVIEW_ID={REAL_REVIEW_ID}")
print("=" * 70)

# ═══════════════════════════════════════════
#  G4 — RAG / Application Knowledge
# ═══════════════════════════════════════════
section("G4 — RAG / Application Knowledge")

# G4.1 — Knowledge documents
section("G4.1 — Knowledge Documents")

rag_planogram = search_application_documentation("planogram file formats upload")
doc_text = rag_planogram.get("documentation", "").lower()
test("G4.1.1 RAG mentions CSV", "csv" in doc_text, f"Found: {'csv' in doc_text}")
test("G4.1.2 RAG mentions XLS", "xls" in doc_text, f"Found: {'xls' in doc_text}")
test("G4.1.3 RAG mentions XLSX", "xlsx" in doc_text, f"Found: {'xlsx' in doc_text}")
test("G4.1.4 RAG mentions JSON", "json" in doc_text, f"Found: {'json' in doc_text}")
test("G4.1.5 RAG does NOT mention PDF", "pdf" not in doc_text, f"Found PDF: {'pdf' in doc_text}")
test("G4.1.6 RAG does NOT mention PowerPoint", "powerpoint" not in doc_text and "pptx" not in doc_text)

# G4.1 Test 2 — Required fields
test("G4.1.7 RAG mentions planogram_id", "planogram_id" in doc_text)
test("G4.1.8 RAG mentions shelf_id", "shelf_id" in doc_text)
test("G4.1.9 RAG mentions position", "position" in doc_text)
test("G4.1.10 RAG mentions sku_id", "sku_id" in doc_text)

# G4.1 Test 3 — Product dependency
test("G4.1.11 RAG mentions SKU must exist in Product Master",
     "product master" in doc_text and "already exist" in doc_text,
     f"Text sample: ...{doc_text[doc_text.find('sku'):doc_text.find('sku')+120]}...")

# G4.2 — Chunking test
section("G4.2 — Document Chunking")

rag_review = search_application_documentation("How does Human Review work")
review_text = rag_review.get("documentation", "").lower()
test("G4.2.1 Human Review query retrieves review content", "human review" in review_text or "recognition_review_threshold" in review_text)
test("G4.2.2 Review query contains threshold info", "threshold" in review_text or "0.40" in review_text)

# G4.3 — Semantic retrieval
section("G4.3 — Embedding + Vector Storage")

rag_semantic = search_application_documentation("define expected shelf arrangement feature")
semantic_text = rag_semantic.get("documentation", "").lower()
test("G4.3.1 Semantic query retrieves planogram docs", "planogram" in semantic_text,
     f"Contains 'planogram': {'planogram' in semantic_text}")

rag_semantic2 = search_application_documentation("specify which SKU goes at each shelf position")
semantic_text2 = rag_semantic2.get("documentation", "").lower()
test("G4.3.2 Position query retrieves planogram docs", "planogram" in semantic_text2 or "position" in semantic_text2)

# G4.4 — ML lifecycle RAG
section("G4.4 — Actual RAG Retrieval")

rag_ml = search_application_documentation("ML system decides product needs manager review")
ml_text = rag_ml.get("documentation", "").lower()
test("G4.4.1 ML review query mentions YOLO", "yolo" in ml_text)
test("G4.4.2 ML review query mentions ResNet", "resnet" in ml_text)
test("G4.4.3 ML review query mentions similarity", "similarity" in ml_text)
test("G4.4.4 ML review query mentions threshold", "threshold" in ml_text)

# ═══════════════════════════════════════════
#  G5 — Context & Role Awareness
# ═══════════════════════════════════════════
section("G5 — Context & Role Awareness")

# G5.3 — Role gating
section("G5.3 — Backend Role Gating")

test("G5.3.1 Employee blocked from manager tools", _require_manager("EMPLOYEE") is not None)
test("G5.3.2 Manager allowed", _require_manager("MANAGER") is None)
test("G5.3.3 Admin allowed", _require_manager("ADMIN") is None)
test("G5.3.4 ADMIN,EMPLOYEE multi-role allowed", _require_manager("ADMIN, EMPLOYEE") is None)

# Security: employee should be blocked from specific tools
employee_pending = get_pending_reviews(db, ORG_ID, "EMPLOYEE")
test("G5.3.5 Employee blocked from get_pending_reviews", "error" in employee_pending, f"Got: {employee_pending.get('error', 'NO ERROR')}")

employee_model = get_model_status(db, ORG_ID, "EMPLOYEE")
test("G5.3.6 Employee blocked from get_model_status", "error" in employee_model)

employee_analytics = get_audit_statistics(db, ORG_ID, "EMPLOYEE")
test("G5.3.7 Employee blocked from get_audit_statistics", "error" in employee_analytics)

employee_violations = get_violation_analytics(db, ORG_ID, "EMPLOYEE")
test("G5.3.8 Employee blocked from get_violation_analytics", "error" in employee_violations)

employee_trend = get_compliance_trend(db, ORG_ID, "EMPLOYEE")
test("G5.3.9 Employee blocked from get_compliance_trend", "error" in employee_trend)

employee_review_stats = get_pending_review_statistics(db, ORG_ID, "EMPLOYEE")
test("G5.3.10 Employee blocked from get_pending_review_statistics", "error" in employee_review_stats)

employee_planogram = get_planogram_status(db, ORG_ID, "EMPLOYEE")
test("G5.3.11 Employee blocked from get_planogram_status", "error" in employee_planogram)

employee_product = get_product_summary(db, ORG_ID, "EMPLOYEE")
test("G5.3.12 Employee blocked from get_product_summary", "error" in employee_product)

employee_ml = get_ml_lifecycle_status(db, ORG_ID, "EMPLOYEE")
test("G5.3.13 Employee blocked from get_ml_lifecycle_status", "error" in employee_ml)

# Employee SHOULD be allowed for these
employee_stores = get_store_compliance_overview(db, ORG_ID, "EMPLOYEE")
test("G5.3.14 Employee allowed for store compliance", "stores" in employee_stores)

if REAL_AUDIT_ID:
    employee_audit = get_audit_summary(db, ORG_ID, "EMPLOYEE", REAL_AUDIT_ID)
    test("G5.3.15 Employee allowed for audit summary", "audit_id" in employee_audit)

# ═══════════════════════════════════════════
#  G6 — Backend Tool Calling
# ═══════════════════════════════════════════
section("G6 — Backend Tool Calling")

# G6.1 — Latest audit
section("G6.1 — Latest Audit")
latest = get_latest_audit(db, ORG_ID, "MANAGER")
test("G6.1.1 get_latest_audit returns data", "audit_id" in latest, f"Keys: {list(latest.keys())}")
test("G6.1.2 Has store_name", "store_name" in latest)
test("G6.1.3 Has compliance", "compliance" in latest)
test("G6.1.4 Has violation_counts", "violation_counts" in latest)
test("G6.1.5 Has violation_details", "violation_details" in latest)
if "compliance" in latest:
    test("G6.1.6 Compliance has availability_rate_percent", "availability_rate_percent" in latest["compliance"])
    test("G6.1.7 Compliance has position_accuracy_percent", "position_accuracy_percent" in latest["compliance"])

# G6.2 — Pending reviews
section("G6.2 — Pending Reviews")
pending = get_pending_reviews(db, ORG_ID, "MANAGER")
test("G6.2.1 get_pending_reviews returns data", "total_pending" in pending, f"Total: {pending.get('total_pending')}")
test("G6.2.2 Has reviews list", "reviews" in pending)
actual_pending_count = db.query(HumanReview).filter(
    HumanReview.organization_id == ORG_ID,
    HumanReview.status == ReviewStatus.PENDING
).count()
test("G6.2.3 Count matches database", pending.get("total_pending") == actual_pending_count,
     f"Tool={pending.get('total_pending')}, DB={actual_pending_count}")

# G6.3 — Audit summary
section("G6.3 — Audit Summary")
if REAL_AUDIT_ID:
    summary = get_audit_summary(db, ORG_ID, "MANAGER", REAL_AUDIT_ID)
    test("G6.3.1 Returns correct audit_id", summary.get("audit_id") == REAL_AUDIT_ID)
    test("G6.3.2 Has definitions", "definitions" in summary)
    test("G6.3.3 Has pending_human_reviews", "pending_human_reviews" in summary)

    # Verify data matches database
    db_comp = db.query(ComplianceResult).filter(ComplianceResult.audit_id == REAL_AUDIT_ID).first()
    if db_comp and summary.get("compliance", {}).get("availability_rate_percent") is not None:
        expected_pct = round(db_comp.availability_rate * 100, 1)
        actual_pct = summary["compliance"]["availability_rate_percent"]
        test("G6.3.4 Compliance matches database", expected_pct == actual_pct,
             f"Expected={expected_pct}, Got={actual_pct}")

    db_violations = db.query(ComplianceViolation).filter(ComplianceViolation.audit_id == REAL_AUDIT_ID).count()
    tool_total = summary.get("violation_counts", {}).get("total", 0)
    test("G6.3.5 Violation count matches database", tool_total == db_violations,
         f"Tool={tool_total}, DB={db_violations}")

    # Tenant isolation test
    fake_audit = get_audit_summary(db, "00000000-0000-0000-0000-000000000000", "MANAGER", REAL_AUDIT_ID)
    test("G6.3.6 Tenant isolation: wrong org gets 'not found'", "error" in fake_audit,
         f"Got: {fake_audit}")

# G6.4 — Model status
section("G6.4 — Model Status")
model = get_model_status(db, ORG_ID, "MANAGER")
test("G6.4.1 Has active_model_version", "active_model_version" in model)
test("G6.4.2 Has pipeline_status", "pipeline_status" in model)
test("G6.4.3 Has total_pending_samples", "total_pending_samples" in model)
test("G6.4.4 Has required_for_training", "required_for_training" in model)
test("G6.4.5 Has ready_to_train boolean", "ready_to_train" in model)
test("G6.4.6 Has samples_uploaded_to_s3", "samples_uploaded_to_s3" in model)

# G6.5 — Navigation
section("G6.5 — Navigation")
nav_products = navigate_to_page("MANAGER", "/manager/products")
test("G6.5.1 Manager can navigate to /manager/products", nav_products.get("action") == "NAVIGATE")
test("G6.5.2 Route is correct", nav_products.get("route") == "/manager/products")

nav_stores = navigate_to_page("MANAGER", "/manager/stores")
test("G6.5.3 Manager can navigate to /manager/stores", nav_stores.get("action") == "NAVIGATE")

nav_reviews = navigate_to_page("MANAGER", "/manager/reviews")
test("G6.5.4 Manager can navigate to /manager/reviews", nav_reviews.get("action") == "NAVIGATE")

# Navigation security
nav_external = navigate_to_page("MANAGER", "https://example.com")
test("G6.5.5 External URL blocked", "error" in nav_external, f"Got: {nav_external}")

nav_employee_to_manager = navigate_to_page("EMPLOYEE", "/manager/reviews")
test("G6.5.6 Employee blocked from manager routes", "error" in nav_employee_to_manager)

nav_employee_home = navigate_to_page("EMPLOYEE", "/employee")
test("G6.5.7 Employee can navigate to /employee", nav_employee_home.get("action") == "NAVIGATE")

nav_employee_audit = navigate_to_page("EMPLOYEE", "/employee/audit/new")
test("G6.5.8 Employee can navigate to /employee/audit/new", nav_employee_audit.get("action") == "NAVIGATE")

nav_invalid = navigate_to_page("MANAGER", "/admin/database")
test("G6.5.9 Invalid route blocked", "error" in nav_invalid)

# ═══════════════════════════════════════════
#  G7 — Natural Language Analytics
# ═══════════════════════════════════════════
section("G7 — Natural Language Analytics")

# G7.1 — Audit statistics
section("G7.1 — Audit Statistics")
stats = get_audit_statistics(db, ORG_ID, "MANAGER", 30)
test("G7.1.1 Has total_all_time", "total_all_time" in stats)
test("G7.1.2 Has total_in_period", "total_in_period" in stats)
test("G7.1.3 Has this_week", "this_week" in stats)
test("G7.1.4 Has by_status", "by_status" in stats)
test("G7.1.5 Has average_compliance_percent", "average_compliance_percent" in stats)

# Verify total matches DB
db_total = db.query(ShelfAudit).filter(ShelfAudit.organization_id == ORG_ID).count()
test("G7.1.6 Total all-time matches DB", stats.get("total_all_time") == db_total,
     f"Tool={stats.get('total_all_time')}, DB={db_total}")

# G7.2 — Store comparison
section("G7.2 — Store Compliance Overview")
stores = get_store_compliance_overview(db, ORG_ID, "MANAGER")
test("G7.2.1 Has stores array", "stores" in stores)
db_store_count = db.query(Store).filter(Store.organization_id == ORG_ID).count()
test("G7.2.2 Store count matches DB", len(stores.get("stores", [])) == db_store_count,
     f"Tool={len(stores.get('stores', []))}, DB={db_store_count}")

for s in stores.get("stores", []):
    test(f"G7.2.3 Store '{s['store_name']}' has compliance field",
         "latest_compliance_percent" in s,
         f"Value: {s.get('latest_compliance_percent')}")

# G7.3 — Violation analytics
section("G7.3 — Violation Analytics")
violations = get_violation_analytics(db, ORG_ID, "MANAGER", 30)
test("G7.3.1 Has total_violations", "total_violations" in violations)
test("G7.3.2 Has by_type", "by_type" in violations)
test("G7.3.3 Has most_common_type", "most_common_type" in violations)
test("G7.3.4 Has by_store", "by_store" in violations)
test("G7.3.5 Has most_problematic_products", "most_problematic_products" in violations)

# G7.4 — Compliance trend
section("G7.4 — Compliance Trend")
trend = get_compliance_trend(db, ORG_ID, "MANAGER", 8)
test("G7.4.1 Has trend array", "trend" in trend)
test("G7.4.2 Has 8 weeks", len(trend.get("trend", [])) == 8,
     f"Got {len(trend.get('trend', []))} weeks")
if trend.get("trend"):
    first_week = trend["trend"][0]
    test("G7.4.3 Week has week_ending", "week_ending" in first_week)
    test("G7.4.4 Week has audits_count", "audits_count" in first_week)
    test("G7.4.5 Week has average_compliance_percent", "average_compliance_percent" in first_week)

# G7.5 — Review statistics
section("G7.5 — Pending Review Statistics")
review_stats = get_pending_review_statistics(db, ORG_ID, "MANAGER")
test("G7.5.1 Has total_pending", "total_pending" in review_stats)
test("G7.5.2 Has total_completed", "total_completed" in review_stats)

# ═══════════════════════════════════════════
#  G8 — Navigation Validation (extended)
# ═══════════════════════════════════════════
section("G8 — Navigation Validation")

all_manager_routes = ["/manager", "/manager/stores", "/manager/products",
                      "/manager/planograms", "/manager/audits", "/manager/reviews", "/manager/employees"]
for route in all_manager_routes:
    r = navigate_to_page("MANAGER", route)
    test(f"G8.1 Manager→{route}", r.get("action") == "NAVIGATE")

# Employee routes
for route in ["/employee", "/employee/audit/new"]:
    r = navigate_to_page("EMPLOYEE", route)
    test(f"G8.2 Employee→{route}", r.get("action") == "NAVIGATE")

# Cross-role blocked
for route in all_manager_routes:
    r = navigate_to_page("EMPLOYEE", route)
    test(f"G8.3 Employee blocked→{route}", "error" in r)

# ═══════════════════════════════════════════
#  G9 — Explain This Audit
# ═══════════════════════════════════════════
section("G9 — Explain This Audit")

if REAL_AUDIT_ID:
    explanation = explain_audit(db, ORG_ID, "MANAGER", REAL_AUDIT_ID)
    test("G9.1 Has audit_id", "audit_id" in explanation)
    test("G9.2 Has compliance", "compliance" in explanation)
    test("G9.3 Has violation_details", "violation_details" in explanation)
    test("G9.4 Has violations_by_shelf", "violations_by_shelf" in explanation)
    test("G9.5 Has explanation_guidance", "explanation_guidance" in explanation)
    test("G9.6 Has definitions", "definitions" in explanation)
    test("G9.7 Definitions include MISSING_PRODUCT", "MISSING_PRODUCT" in explanation.get("definitions", {}))
    test("G9.8 Definitions include FACING_MISMATCH", "FACING_MISMATCH" in explanation.get("definitions", {}))

    # Check violation details have shelf/position/product
    if explanation.get("violation_details"):
        v = explanation["violation_details"][0]
        test("G9.9 Violation has shelf", "shelf" in v)
        test("G9.10 Violation has position", "position" in v)
        test("G9.11 Violation has type", "type" in v)

    # FACING_MISMATCH definition should NOT say "facing the wrong direction"
    facing_def = explanation.get("definitions", {}).get("FACING_MISMATCH", "")
    test("G9.12 Facing def does NOT say 'wrong direction'", "wrong direction" not in facing_def.lower())

# ═══════════════════════════════════════════
#  G10 — Human Review Copilot
# ═══════════════════════════════════════════
section("G10 — Human Review Copilot")

if REAL_REVIEW_ID:
    review_explain = explain_review(db, ORG_ID, "MANAGER", REAL_REVIEW_ID)
    test("G10.1 Has review_id", "review_id" in review_explain)
    test("G10.2 Has predicted_product", "predicted_product" in review_explain)
    test("G10.3 Has similarity", "similarity" in review_explain)
    test("G10.4 Has review_threshold", "review_threshold" in review_explain)
    test("G10.5 Has reason_for_review", "reason_for_review" in review_explain)
    test("G10.6 Has explanation_guidance", "explanation_guidance" in review_explain)

    # Employee should be blocked
    employee_review = explain_review(db, ORG_ID, "EMPLOYEE", REAL_REVIEW_ID)
    test("G10.7 Employee blocked from explain_review", "error" in employee_review)

    # Tenant isolation
    fake_review = get_review_detail(db, "00000000-0000-0000-0000-000000000000", "MANAGER", REAL_REVIEW_ID)
    test("G10.8 Tenant isolation: wrong org gets 'not found'", "error" in fake_review)
else:
    test("G10.1 SKIP — No reviews in DB", True, "No review data available")

# ═══════════════════════════════════════════
#  G11 — ML Lifecycle
# ═══════════════════════════════════════════
section("G11 — ML Lifecycle Assistant")

ml_status = get_ml_lifecycle_status(db, ORG_ID, "MANAGER")
test("G11.1 Has pipeline steps", "pipeline" in ml_status)
test("G11.2 Pipeline has 6 steps", len(ml_status.get("pipeline", {})) == 6)
test("G11.3 Has active_model", "active_model" in ml_status)
test("G11.4 Has training_status", "training_status" in ml_status)
test("G11.5 Has samples", "samples" in ml_status)
test("G11.6 Has reviews", "reviews" in ml_status)
test("G11.7 Has thresholds", "thresholds" in ml_status)

# Sample details
samples = ml_status.get("samples", {})
test("G11.8 Samples has total", "total" in samples)
test("G11.9 Samples has uploaded_to_s3", "uploaded_to_s3" in samples)
test("G11.10 Samples has failed_upload", "failed_upload" in samples)
test("G11.11 Samples has required_for_training", "required_for_training" in samples)
test("G11.12 Samples has ready_to_train", "ready_to_train" in samples)

# Thresholds
thresholds = ml_status.get("thresholds", {})
test("G11.13 Has review_threshold", "review_threshold" in thresholds)
test("G11.14 Has min_training_samples", "min_training_samples" in thresholds)

# Employee blocked
employee_ml_2 = get_ml_lifecycle_status(db, ORG_ID, "EMPLOYEE")
test("G11.15 Employee blocked from ML lifecycle", "error" in employee_ml_2)

# ═══════════════════════════════════════════
#  Tool count verification
# ═══════════════════════════════════════════
section("Tool Registration")
test("Total tools registered", len(TOOLS) == 17, f"Got {len(TOOLS)}")

tool_names = [t["function"]["name"] for t in TOOLS]
expected_tools = [
    "get_store_compliance_overview", "get_audit_summary", "get_latest_audit",
    "get_pending_reviews", "get_review_detail", "get_model_status",
    "get_planogram_status", "get_product_summary",
    "get_audit_statistics", "get_violation_analytics", "get_compliance_trend",
    "get_pending_review_statistics", "navigate_to_page",
    "explain_audit", "explain_review", "get_ml_lifecycle_status",
    "search_application_documentation"
]
for t in expected_tools:
    test(f"Tool '{t}' registered", t in tool_names)

# ═══════════════════════════════════════════
#  Product & Planogram tools
# ═══════════════════════════════════════════
section("G6 — Product & Planogram Tools")

products = get_product_summary(db, ORG_ID, "MANAGER")
test("G6.P1 Has total_products", "total_products" in products)
test("G6.P2 Has brands", "brands" in products)
test("G6.P3 Has sample_products", "sample_products" in products)

planograms = get_planogram_status(db, ORG_ID, "MANAGER")
test("G6.PL1 Has total_planograms", "total_planograms" in planograms)
test("G6.PL2 Has planograms list", "planograms" in planograms)

# ═══════════════════════════════════════════
#  Dispatcher test
# ═══════════════════════════════════════════
section("Dispatcher")

# Test execute_tool passes role correctly
dispatch_result = execute_tool("get_pending_reviews", {}, db, ORG_ID, "EMPLOYEE", None)
test("Dispatcher passes role to tool (employee blocked)", "error" in dispatch_result)

dispatch_result2 = execute_tool("get_pending_reviews", {}, db, ORG_ID, "MANAGER", None)
test("Dispatcher passes role to tool (manager allowed)", "total_pending" in dispatch_result2)

dispatch_result3 = execute_tool("unknown_tool", {}, db, ORG_ID, "MANAGER", None)
test("Dispatcher handles unknown tool", "error" in dispatch_result3)

# ═══════════════════════════════════════════
#  RESULTS
# ═══════════════════════════════════════════
db.close()

print("\n" + "=" * 70)
print("TEST RESULTS")
print("=" * 70)

current_section = ""
for status, name, detail in RESULTS:
    if status == "SECTION":
        current_section = name
        print(f"\n{'─' * 50}")
        print(f"  {name}")
        print(f"{'─' * 50}")
    elif status == "PASS":
        print(f"  ✅ {name}" + (f"  ({detail})" if detail else ""))
    else:
        print(f"  ❌ {name}" + (f"  ({detail})" if detail else ""))

print(f"\n{'=' * 70}")
print(f"  TOTAL: {PASS + FAIL}  |  ✅ PASS: {PASS}  |  ❌ FAIL: {FAIL}")
print(f"  Pass Rate: {PASS / (PASS + FAIL) * 100:.1f}%")
print(f"{'=' * 70}")

sys.exit(0 if FAIL == 0 else 1)

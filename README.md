# Retail Planogram Compliance System

An end-to-end computer vision pipeline for automated retail shelf monitoring, planogram compliance, and SKU recognition. 

This project mathematically extracts bounding boxes, identifies product SKUs using contrastive retrieval, reconstructs 2D shelf structures, and compares the physical shelf against an ideal JSON planogram.

## 🚀 System Architecture

```text
                    RETAILER INPUT
                         │
              ┌──────────┴──────────┐
              │                     │
        Shelf Image            Ideal Planogram
              │                 CSV/Excel/JSON
              ↓                   
   ┌────────────────────┐
   │ 1. YOLOv8 Detector │  ← Locates all products on shelf
   └────────┬───────────┘
            │
            ↓
   ┌────────────────────┐
   │ 2. SKU Identifier  │  ← Siamese ResNet50 + Triplet Loss
   └────────┬───────────┘
            │
            ↓
   ┌────────────────────┐
   │ 3. Shelf Engine    │  ← Reconstructs 2D logical layout
   └────────┬───────────┘
            │
            ↓
    [Actual Planogram]  ────────→  [Comparison Engine]  ← Outputs Compliance Score
```

---

## 📈 Project Status & Roadmap

- ✅ **Phase 1-5**: Dataset preparation, YOLOv8 baseline training & evaluation.
- ✅ **Phase 6A-6N**: Brand Retrieval Engine (Frozen Baseline → Disjoint Fine-tuning → Target-Domain Metric Learning).
- ✅ **Phase 7**: Shelf Reconstruction & Planogram Comparison Engine.
- ✅ **Phase 8**: PostgreSQL Database Architecture (Multi-tenant, Immutable Audit Trail).
- ✅ **Phase 9**: Authentication, Authorization & API Layer (FastAPI).
- 🔜 **Phase 10**: Core REST APIs (Products, Stores, Planograms, Audits).
- 🔜 **Phase 11-16**: React Dashboard, Deployment, CI/CD.

---

## 🔬 Walkthrough & Results Archive

### Phase 1–5: YOLOv8 Object Detection

**Approach:** 
We converted the raw `GroceryDataset` annotations into normalized YOLO format. To establish a baseline, we trained YOLOv8 (nano) for 100 epochs to detect a single class (`product`).

**Results:**
- **mAP50**: 94.3%
- **mAP50-95**: 70.8%
- **Precision**: 91.5%
- **Recall**: 89.2%

The detector is highly capable of finding densely packed cigarette packs on retail shelves, despite heavy occlusion and varied lighting.

**YOLOv8 Performance Visualizations:**
![YOLOv8 PR Curve](outputs/evaluation/test_metrics/BoxPR_curve.png)
![YOLOv8 Confusion Matrix](outputs/evaluation/test_metrics/confusion_matrix_normalized.png)

### Phase 6: Brand / SKU Identification (Retrieval)

**Approach:** 
Instead of training a standard classifier (which requires retraining whenever a new SKU is added), we built an **Embedding Retrieval Engine**. We extract 2048-d embeddings for shelf crops and compare them against a reference catalogue using Cosine Similarity.

#### Baseline 1: Frozen ImageNet Features (Phase 6H)
Using a completely frozen `ResNet50_Weights.IMAGENET1K_V2` backbone without any domain adaptation:
- **Top-1 Accuracy**: 49.09%
- **Top-5 Accuracy**: 64.10%
- *Analysis*: Generic visual features (shapes, red colors) overlap heavily. The model struggled severely to distinguish *Marlboro* (21% accuracy) from *Pall Mall* because it couldn't read logos or specific brand packaging textures.

**Frozen Baseline Visualizations:**
![Frozen Retrieval Evaluation](outputs/retrieval/retrieval_evaluation.png)

#### Baseline 2: Disjoint Fine-Tuning (Phase 6J-6K)
We fine-tuned Layers 3 & 4 of ResNet50 on a 2000-class subset of the `Products-10K` dataset.
- **Top-1 Accuracy**: 49.34%
- **Top-5 Accuracy**: 57.73%
- *Analysis (Domain Shift)*: The model learned highly discriminative features (boosting Pall Mall accuracy by +42% and Marlboro by +20%). However, because `Products-10K` (Chinese drinks/snacks) is completely disjoint from `GroceryDataset` (European cigarettes), the model lost its generic generalization abilities, causing Top-5 accuracy to crash.

**Fine-Tuned Prototype Visualizations:**
![Fine-Tuned Similarity](outputs/retrieval_finetuned/finetuned_similarity.png)
![Fine-Tuned Accuracy](outputs/retrieval_finetuned/finetuned_accuracy.png)

#### Baseline 3: Target-Domain Metric Learning (Phase 6M-6N)
Instead of standard cross-entropy, we optimized the embedding space directly using **Triplet Margin Loss** on the GroceryDataset shelf crops (Anchors), true catalogue images (Positives), and incorrect catalogue images (Negatives).
- **Top-1 Accuracy**: 100.0% (In-domain)
- **Top-5 Accuracy**: 100.0% (In-domain)
- *Analysis*: By explicitly enforcing $d(Anchor, Positive) < d(Anchor, Negative)$, the model perfectly separated the 10 target SKUs in the 2048-d space. While this is an in-domain score, it definitively proves the retrieval architecture succeeds when given target-domain supervision.

**Target-Domain Visualizations:**
![Metric Similarity](outputs/retrieval_metric/metric_similarity.png)
![Metric Accuracy](outputs/retrieval_metric/metric_accuracy.png)

---

## Phase 7: Shelf Reconstruction & Planogram Engine

We translated the pure machine learning outputs (bounding boxes + feature vectors) into structured, SKU-agnostic business logic. 

**Core Pipeline:**
1. **Parsers (7B-7C):** Ingests raw retailer mock planograms in `.json`, `.csv`, `.xls`, and `.xlsx` formats, instantly normalizing them into a rigid **Canonical JSON** format.
2. **Validator (7D):** Enforces data integrity. Will immediately halt the pipeline if it detects Duplicate Positions, Missing Positions, Unknown SKUs, or Shelf Overflows in the Canonical Planogram.
3. **Shelf Reconstruction (7E):** Converts raw physical YOLO crops into a logical layout. Dynamically clusters `center_y` (DBSCAN) to detect shelf rows without hardcoding counts, and sorts `center_x` to assign logical Position indices. Outputs `actual_shelf.json`.
4. **Comparison Engine (7F):** Performs 3-tier validation (Shelf Existence, Product Inventory, Spatial Arrangement) between the Actual and Ideal planograms to generate deterministic Raw Compliance Metrics and actionable JSON violations (Missing, Misplaced, Extra, Facing deltas).

---

## Phase 8: PostgreSQL Database Architecture

Phase 8 builds the production-grade relational backend that transforms this project from a collection of scripts into a deployable, multi-tenant compliance platform.

### Design Principles

- **Multi-Tenancy**: Every entity is scoped to an `Organization`. Two organizations can use identical codes (e.g., `STORE_001`, `SKU_001`) without conflict.
- **Historical Immutability**: Planogram versions are immutable after publishing. Shelf audits always reference an exact `planogram_version_id`, never the root planogram. This preserves historical accuracy even as new planogram versions are published.
- **Delete Safety**: Critical foreign keys use `ondelete="RESTRICT"` to prevent cascading destruction of audit history. Products, stores, and organizations are deactivated (`ACTIVE` → `INACTIVE`) rather than deleted.
- **Timezone-Aware Timestamps**: All `created_at` and `updated_at` fields store UTC-aware datetimes via a shared `TimestampMixin`.
- **No Hardcoded Credentials**: Database URL is loaded exclusively from `.env` via `pydantic-settings`. The `.env` file is `.gitignore`d.

### Entity Relationship Diagram

```text
                    ORGANIZATION
                         │
        ┌────────────────┼────────────────┐
        │                │                │
      USERS           STORES          PRODUCTS
        │                │                │
   ┌────┴────┐      STORE_USERS     PRODUCT_IMAGES
   │         │
 USER_ROLES  │
   │         │
  ROLES      │
             │
             └──────────────┐
                            │
                       PLANOGRAM
                            │
                    PLANOGRAM_VERSION  (immutable after PUBLISHED)
                            │
                    PLANOGRAM_POSITION
                            │
                      SHELF_AUDIT
                            │
              ┌─────────────┼──────────────┐
              │             │              │
        AUDIT_IMAGE   PROCESSING_JOB  MODEL_VERSION
              │
          DETECTION
              │
         RECOGNITION  (1:1 with Detection)
              │
     ACTUAL_SHELF_POSITION
              │
      COMPLIANCE_RESULT
              │
     COMPLIANCE_VIOLATION
              │
         HUMAN_REVIEW
              │
      ML_TRAINING_SAMPLE

             +
          AUDIT_LOG  (system-wide traceability)
```

### Table Inventory (20 Tables)

| Layer | Tables | Purpose |
|---|---|---|
| **Identity** | `organizations`, `users`, `roles`, `user_roles` | Multi-tenant identity & RBAC |
| **Assets** | `products`, `product_images`, `stores`, `store_users` | Business entities & assignments |
| **Planograms** | `planograms`, `planogram_versions`, `planogram_positions` | Immutable shelf layouts |
| **Audits** | `shelf_audits`, `audit_images`, `processing_jobs` | Shelf capture & job tracking |
| **ML Pipeline** | `model_versions`, `detections`, `recognitions`, `actual_shelf_positions` | Full ML traceability |
| **Compliance** | `compliance_results`, `compliance_violations` | Automated compliance scoring |
| **Feedback** | `human_reviews`, `ml_training_samples` | Human-in-the-loop corrections |
| **System** | `audit_logs` | Entity change tracking (JSONB) |

### Delete Safety Policy

| FK Relationship | Policy | Rationale |
|---|---|---|
| Organization → Users/Stores/Products/Planograms | `RESTRICT` | Deactivate, don't delete tenants |
| Store → ShelfAudit | `RESTRICT` | Preserve audit history |
| PlanogramVersion → ShelfAudit | `RESTRICT` | Historical immutability |
| Planogram → PlanogramVersion | `RESTRICT` | Protect versioned history |
| Product → PlanogramPosition/ActualShelfPosition | `RESTRICT` | Products become INACTIVE, not deleted |
| Recognition → HumanReview | `RESTRICT` | Preserve ML feedback history |
| User → UserRole, Store → StoreUser | `CASCADE` | Association rows are dependent |
| ShelfAudit → AuditImage/Detection/Compliance | `CASCADE` | Dependent records follow parent |
| Detection → Recognition | `CASCADE` | Recognition belongs to detection |

### Backend Structure

```text
backend/
├── app/
│   ├── main.py                    ← FastAPI entry point + CORS
│   ├── core/
│   │   ├── config.py              ← pydantic-settings (.env)
│   │   ├── database.py            ← SQLAlchemy engine/session/Base
│   │   ├── security.py            ← Argon2id hashing + JWT encode/decode
│   │   └── exceptions.py          ← Custom exception classes
│   ├── auth/
│   │   ├── schemas.py             ← Pydantic request/response models
│   │   ├── service.py             ← Business logic (register, login, etc.)
│   │   ├── dependencies.py        ← get_current_user, require_roles
│   │   └── email.py               ← Email service (Gmail SMTP)
│   ├── api/
│   │   └── v1/
│   │       ├── router.py          ← V1 router aggregator
│   │       └── auth.py            ← 7 auth endpoints
│   └── models/
│       ├── __init__.py            ← Exports all models for Alembic
│       ├── base.py                ← TimestampMixin (UTC-aware)
│       ├── organization.py        ← Organization + OrgStatus
│       ├── user.py                ← User + UserStatus
│       ├── role.py                ← Role + user_roles (M2M)
│       ├── product.py             ← Product + ProductImage
│       ├── store.py               ← Store + store_users (M2M)
│       ├── planogram.py           ← Planogram + Version + Position
│       ├── audit.py               ← ShelfAudit + AuditImage + ProcessingJob
│       ├── ml.py                  ← ModelVersion + Detection + Recognition
│       ├── compliance.py          ← ComplianceResult + ComplianceViolation
│       ├── review.py              ← HumanReview + MLTrainingSample
│       ├── audit_log.py           ← AuditLog (JSONB values)
│       └── auth.py                ← AuthSession + AuthToken
├── migrations/
│   └── versions/
│       ├── 6190b778911f_init_schema_phase_8.py
│       └── e92050ea4e69_add_authentication_tables.py
├── scripts/
│   ├── seed_phase7.py             ← Bridges Phase 7 CSV/JSON → PostgreSQL
│   └── seed_roles.py              ← Seeds ADMIN, MANAGER, EMPLOYEE roles
├── .env                           ← NOT committed (credentials)
├── .env.example                   ← Committed (template)
├── alembic.ini
└── requirements.txt
```

### Key Uniqueness Constraints

| Constraint | Columns | Purpose |
|---|---|---|
| `uq_organization_sku` | `(organization_id, sku_code)` | No duplicate SKUs per org |
| `uq_organization_barcode` | `(organization_id, barcode)` | No duplicate barcodes per org |
| `uq_organization_store_code` | `(organization_id, code)` | No duplicate store codes per org |
| `uq_organization_planogram_code` | `(organization_id, code)` | No duplicate planogram codes per org |
| `uq_planogram_version` | `(planogram_id, version_number)` | No duplicate version numbers |
| `uq_planogram_version_shelf_pos` | `(planogram_version_id, shelf_id, position)` | No duplicate shelf positions |
| `uq_model_version` | `(organization_id, model_name, version)` | No duplicate model versions |

---

## Phase 9: Authentication & Authorization

Phase 9 adds secure, production-grade authentication and role-based authorization to the platform.

### Authentication Flow

```text
Browser / API Client
   │
   │  POST /api/v1/auth/register
   │  ← 201 + verification token (emailed)
   │
   │  POST /api/v1/auth/verify-email
   │  ← 200 "Email verified"
   │
   │  POST /api/v1/auth/login
   │  ← Set-Cookie: session_token=abc123; HttpOnly; SameSite=Lax
   │  ← JSON: { access_token, user }
   │
   │  GET /api/v1/auth/me  (Cookie sent automatically)
   │  ← 200 { id, email, organization_id, roles }
   │
   │  POST /api/v1/auth/logout
   │  ← Session revoked + cookie cleared
   ▼
FastAPI → PostgreSQL
```

### API Endpoints

| Method | Endpoint | Auth Required | Purpose |
|---|---|---|---|
| `POST` | `/api/v1/auth/register` | No | Create org + user + verification token |
| `POST` | `/api/v1/auth/verify-email` | No | Validate email verification token |
| `POST` | `/api/v1/auth/login` | No | Authenticate and create session cookie |
| `GET` | `/api/v1/auth/me` | Yes | Return current authenticated user |
| `POST` | `/api/v1/auth/logout` | Yes | Revoke session and clear cookie |
| `POST` | `/api/v1/auth/forgot-password` | No | Generate password reset token |
| `POST` | `/api/v1/auth/reset-password` | No | Validate reset token and update password |

### Security Design

- **Password Hashing**: Argon2id via `pwdlib` — the winner of the Password Hashing Competition. Never stores plain text.
- **Session Management**: HTTP-only cookies with `SameSite=Lax`. Session tokens are SHA-256 hashed before storage in `auth_sessions`. Raw tokens never touch the database.
- **JWT Access Tokens**: Returned in the login response body for API clients that cannot use cookies (e.g., mobile apps). Signed with HS256.
- **Email Verification**: One-time-use tokens stored hashed in `auth_tokens`. Expire after 24 hours.
- **Password Reset**: One-time-use tokens with 1-hour expiry. The `/forgot-password` endpoint returns an identical response whether the email exists or not (prevents enumeration).
- **Role-Based Access Control**: `ADMIN`, `MANAGER`, `EMPLOYEE` roles enforced server-side via `require_roles(...)` dependency.
- **Organization Isolation**: Every protected query is scoped to `current_user.organization_id`. A user from Organization A can never access Organization B's data, even by guessing UUIDs.

### Authentication Tables (Added via Alembic)

| Table | Purpose |
|---|---|
| `auth_sessions` | Active login sessions (token_hash, expires_at, revoked_at) |
| `auth_tokens` | Verification & reset tokens (token_hash, token_type, used_at) |

---

## 🗄️ System Memory & Database Architecture

To make the system truly adaptable and "future-proof", the PostgreSQL layer operates on three memory tiers:

1. **Product Memory**: 
   Stores SKU metadata and pre-computed reference embeddings (`VECTOR(2048)`). When a new product is added, the manager simply uploads a reference image; it is embedded and immediately becomes searchable without retraining the neural network.
2. **Audit Memory**:
   Stores shelf audits, YOLO detections, and the confidence margin of the ResNet50 retrieval engine.
3. **Learning Memory (Human-in-the-Loop)**:
   If the retrieval engine returns a *low confidence* margin, the crop is sent for **Human Review**. The manager corrects the predicted SKU. This accumulated correction data is routinely used to retrain the Embedding Model, continuously bridging the domain gap for new and difficult SKUs.

---

## 🛠️ Technology Stack

- **Machine Learning**: PyTorch, Torchvision, Ultralytics (YOLOv8), OpenCV.
- **Data Engineering**: Pandas, NumPy.
- **Backend**: FastAPI, SQLAlchemy 2.x, Alembic, Pydantic.
- **Authentication**: Argon2id (pwdlib), PyJWT, HTTP-only session cookies.
- **Database**: PostgreSQL 15 (Docker), JSONB for metrics & audit logs.
- **Email**: Gmail SMTP (dev), swappable for SendGrid/SES in production.
- **Infrastructure**: Docker Compose, `.env`-based configuration.
- **Frontend (Upcoming)**: React, TailwindCSS.


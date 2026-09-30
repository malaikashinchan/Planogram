# Getting Started with Planogram Compliance

## Welcome
Welcome to the Planogram Compliance Platform! This tool helps retail organizations measure and enforce shelf compliance using Computer Vision and Machine Learning.

## Core Concepts
1. **Organizations**: Every user and entity belongs to an Organization. This ensures strict tenant isolation.
2. **Stores**: Physical retail locations. Managers can create stores, place them on a map, and assign Planograms to them.
3. **Planograms**: The idealized layout of products on a shelf.

## Planogram Upload

Managers can upload planograms from the Planograms page.

Supported formats:
- CSV
- XLS
- XLSX
- JSON

The uploaded planogram must follow the application's required schema.

The backend validates:
- planogram_id
- version
- shelf_id
- position
- sku_id

SKUs referenced by the planogram must already exist in the organization's Product Master.

The system creates a new immutable planogram version after successful validation.

4. **Audits**: Employees take a picture of the shelf. The ML pipeline runs Object Detection (YOLO) and Metric Learning (ResNet) to reconstruct the shelf and compare it to the assigned planogram.

## How to use the platform
- **Managers**: Import your Product Master, create Stores, upload Planograms, and review Audits on the Dashboard.
- **Employees**: Use the mobile-friendly Audit Wizard to select a store, choose a planogram, and capture an image of the shelf.

## Troubleshooting
If an audit fails with "NEEDS_RETAKE", it means the YOLO model could not find any products. Ensure good lighting and a clear view of the shelf.

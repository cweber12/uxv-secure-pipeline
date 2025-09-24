# Cloud (Ingest API, Storage, Analytics)

## Purpose

- Provide an authenticated ingest API (behind gateway).
- Store artifacts (MP4, telemetry JSON, detections JSON) in S3-like storage.
- Run batch analytics (detections over time, heatmaps).
- Manage IAM roles, KMS encryption, and audit logging.
- IaC (Terraform) for reproducibility.

## Components (planned)

- `api/` (FastAPI/Go, signed URLs, RBAC)
- `analytics/` (batch jobs, notebooks)
- `iac/` (Terraform modules for bucket, KMS, roles, gateway)

## Storage Layout (example)

s3://missions/<mission_id>/
video.mp4
telemetry.jsonl
detections.jsonl
index.json

markdown
Copy code

## Security

- OIDC→STS (no static creds).
- KMS envelope encryption.
- Access logs + retention policies.
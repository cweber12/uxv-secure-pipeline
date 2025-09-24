# Standards Mapping (Skeleton)

> Not claiming formal compliance—this map shows awareness and direction.

## MISB 0601 (KLV)

- **Planned**: Embed basic platform position, timestamp, and sensor metadata into stream.
- **Artifacts**: KLV pack/unpack unit tests; ground KLV extractor verification.

## NIST 800-53 (selected controls)

- **AC-2**: Role-based access in Ground/Cloud; short-lived creds.
- **CM-2**: Versioned protos; ADRs for changes.
- **SC-8/SC-13**: mTLS in transit; KMS envelope encryption at rest.
- **SI-10**: Input validation & fuzzing for parsers.
- **AU-2/AU-12**: Audit logs for mission ingest & access.

## DO-178C-style Trace (lightweight)

- **Req→Test mapping** in `docs/arch.md` (tables TBD).
- Latency & pairing metrics reported by CI job.
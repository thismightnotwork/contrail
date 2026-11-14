# Contrail + ACARS on Railway

Deploy this fork as a new Railway service from the root Dockerfile, branch master. No custom start command. Generate a public domain. Health check: /health. The container honours PORT, binds 0.0.0.0 and defaults to DEMO_MODE=0 (real ADSB.lol provider).

Attach a volume to this new service at /data. The old service's volume does not transfer automatically. Keep one replica/process; disable application sleeping for continuous collection. Leave BASE_PATH empty.

Defaults: DATA_DIR=/data; ARCHIVE_DB_PATH=/data/acars.sqlite3 (derived from DATA_DIR); ACARS_RETENTION_DAYS=7; ACARS_MAX_MESSAGES=20000; ACARS_MAX_PAYLOAD_MB=128. The first retention limit reached removes oldest records. Payload budget excludes SQLite index/page overhead; monitor actual disk usage. Deleted pages are reused, not necessarily returned to the filesystem.

Open / for the map, /acars for Top 500 and registration history. Selected aircraft panels contain Recorded ACARS, 100 messages per page. The top 500 ranks the retained archive, not all-time history. Raw metadata is expandable. Above 64 KiB raw metadata is omitted with a notice; normalised text and identity remain. Text is capped at 20000 characters.

Airframes sampled stream only: no historical backfill, no guarantee of all messages, no API key, no upstream REST polling and no UDP output. The previous app/database is untouched and not imported. Match by explicit aircraft ICAO24 or normalised registration, excluding conflicting ICAO24; never callsign alone or arbitrary from/to addresses. Direction is the supplied link_direction value or unknown. Scores are keyword/readability heuristics, not confirmed emergencies or reliable humour detection. Browser-only custom rules are not migrated.

Position coverage, throttling, cache-age display, attribution and licences remain upstream Contrail's. Do not evade provider limits. Access/feed errors stop ACARS collection; resolve the issue and restart. Normal network reconnections use Socket.IO backoff. Saved history remains readable while offline. Public read-only UI: messages can contain sensitive information; not an operational aviation tool.

Local checks passed for seven archive cases and JavaScript syntax/build-patch smoke checks. Full Docker/Svelte build, live feeds and Railway deployment were not verified. Retain upstream LICENSE and 3rdparty_licenses.md.

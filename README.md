# RemoteJobsAPI

![RemoteJobsAPI logo](assets/remotejobs-api-logo-500.png)

RemoteJobsAPI is a production-ready Flask API that aggregates remote job listings
from public job-board feeds and exposes them through one clean, normalized
contract. It is designed for RapidAPI consumers who want fresh remote jobs
without building source-specific parsers, deduplication, filtering, pagination,
or cache logic themselves.

## Why it is useful

- Real remote-job data from public sources.
- Normalized response shape across multiple job boards.
- Search, filters, pagination, detail lookup, source metadata, and stats.
- Persistent cache so the API can keep serving the last successful snapshot if a
  source is temporarily down.
- Safe refresh behavior with optional admin token protection.
- Source attribution included for transparent downstream usage.

## Data Sources

The production configuration currently uses:

- Jobicy public API: `https://jobicy.com/api/v2/remote-jobs`
- Himalayas Remote Jobs API: `https://himalayas.app/jobs/api`

Always keep the original `url`, `source`, and `source_domain` fields in consumer
apps so users can apply through the original job posting.

Both sources require attribution/link-back when their jobs are displayed. The
API preserves the original application URL and source fields so buyers can meet
those requirements. Remotive is intentionally not enabled in the commercial
configuration because its public feed is not the right basis for this paid
product. The production refresh interval is intentionally conservative: Jobicy
asks integrations to fetch only a few times per day, while Himalayas refreshes
its public data daily.

## Endpoints

### `GET /`

API status, available endpoints, and current cache metadata.

### `GET /health`

Lightweight health check.

### `GET /jobs`

Returns normalized remote jobs.

Query parameters:

| Name | Description | Example |
| --- | --- | --- |
| `q` or `search` | Text search across title, company, location, category, tags, and description | `python` |
| `company` | Filter by company name | `stripe` |
| `location` | Filter by candidate location text | `latam` |
| `category` | Filter by normalized category | `software` |
| `tag` | Filter by tag/skill | `react` |
| `source` | Filter by source | `himalayas` |
| `limit` | Page size, capped by `MAX_LIMIT` | `25` |
| `offset` | Pagination offset | `50` |
| `sort` | `newest`, `company`, or `title` | `newest` |
| `include_description` | Include full text description | `true` |

Example:

```bash
curl "https://YOUR_HOST/jobs?q=python&location=latam&limit=10"
```

Response shape:

```json
{
  "metadata": {
    "api": "RemoteJobsAPI",
    "version": "2.2.0",
    "updated_at": "2026-06-01T18:30:00+00:00",
    "job_count": 250,
    "sources": ["jobicy", "himalayas"],
    "total": 12,
    "limit": 10,
    "offset": 0,
    "returned": 10
  },
  "jobs": [
    {
      "id": "b7b2a3e081cf03c9",
      "title": "Senior Python Engineer",
      "company": "Example Co",
      "location": "Worldwide",
      "category": "Software Development",
      "tags": ["python", "django", "backend"],
      "salary": "$70000 - $120000",
      "url": "https://example.com/job",
      "source": "himalayas",
      "source_domain": "example.com",
      "published_at": "2026-06-01T12:00:00+00:00",
      "remote": true
    }
  ]
}
```

### `GET /jobs/<id>`

Returns one job by normalized id, including the full description.

### `GET /stats`

Returns total jobs, source counts, top categories, and top locations.

### `GET /sources`

Returns source URLs and attribution notes.

### `POST /refresh`

Manually refreshes the cache. By default this endpoint is disabled unless you set
one of:

- `ADMIN_REFRESH_TOKEN`: requires `Authorization: Bearer <token>`.
- `ALLOW_PUBLIC_REFRESH=true`: allows public refreshes. Not recommended for
  production.

## Environment Variables

| Name | Default | Description |
| --- | --- | --- |
| `PORT` | `5000` | Server port |
| `JOBS_DATABASE_FILE` | `datos_empleos.json` | Persistent cache path |
| `REFRESH_INTERVAL_SECONDS` | `43200` | Successful snapshot refresh interval |
| `FAILURE_RETRY_SECONDS` | `900` | Retry interval after all sources fail |
| `SOURCE_TIMEOUT_SECONDS` | `15` | Per-source HTTP timeout |
| `MAX_LIMIT` | `100` | Maximum `GET /jobs` page size |
| `DEFAULT_LIMIT` | `25` | Default `GET /jobs` page size |
| `ENABLED_SOURCES` | `jobicy,himalayas` | Comma-separated source list |
| `HIMALAYAS_MAX_PAGES` | `5` | Maximum 20-job pages collected per refresh |
| `REFRESH_ON_STARTUP` | `false` | Start a background refresh on boot; keep false with Gunicorn |
| `ENABLE_BACKGROUND_REFRESH` | `true` | Enable scheduled refresh loop |
| `ADMIN_REFRESH_TOKEN` | unset | Protects `POST /refresh` |
| `CORS_ORIGINS` | `*` | CORS origin policy |
| `REQUIRE_PAID_GATEWAY` | `true` | Require an authorized marketplace secret |
| `PAID_GATEWAY_SECRETS` | unset | Comma-separated marketplace proxy secrets |

## Production Security

The Render Blueprint enables paid-gateway protection. Only `/health` remains
public for uptime monitoring. Job data and all other endpoints require a private
marketplace gateway header, so the direct Render URL is not a free customer
endpoint.

For local development only, explicitly set `REQUIRE_PAID_GATEWAY=false`.

## Local Development

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python server.py
```

Then open:

```text
http://localhost:5000/jobs?limit=5
```

## Deployment

Recommended start command:

```bash
gunicorn server:app
```

The production Blueprint keeps background loops disabled. `/health` and
job-reading endpoints refresh a successful snapshot after 12 hours, retry a
failed refresh after 15 minutes, and continue serving the last successful
snapshot during temporary source outages.

## RapidAPI Listing Copy

Marketplace logo:

```text
assets/remotejobs-api-logo-500.png
```

Short description:

```text
Normalized remote job listings from public job-board feeds, with search,
filters, pagination, stats, and source attribution.
```

Long description:

```text
RemoteJobsAPI gives developers one clean feed of remote jobs aggregated from
public job-board sources. It normalizes different source formats into one
contract, deduplicates listings, adds filters for title, company, location,
category, tags and source, and serves cached data so client apps stay reliable
even when an upstream source is temporarily unavailable.
```

Suggested tags:

```text
remote jobs, jobs api, hiring, recruitment, developer jobs, latam jobs, work from home, job search
```

## Recommended Marketplace Plans

- **Starter**: USD 4.99/month, 1,000 requests/month.
- **Pro**: USD 9.99/month, 10,000 requests/month.
- **Ultra**: USD 29/month, 50,000 requests/month.
- **Mega**: USD 79/month, 200,000 requests/month.

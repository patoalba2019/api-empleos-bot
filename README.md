# RemoteJobsAPI

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

The API currently uses:

- Remotive public API: `https://remotive.com/api/remote-jobs`
- Remote OK public JSON feed: `https://remoteok.com/api`

Always keep the original `url`, `source`, and `source_domain` fields in consumer
apps so users can apply through the original job posting.

Before monetizing, review each source's current terms. Remotive's public API asks
developers to mention Remotive as a source and link back to the job URL. If you
want to run this as a paid RapidAPI product, the safest setup is to keep source
attribution visible and disable any source whose terms do not fit your business
model.

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
| `source` | Filter by source | `remotive` |
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
    "version": "2.0.0",
    "updated_at": "2026-06-01T18:30:00+00:00",
    "job_count": 250,
    "sources": ["remotive", "remoteok"],
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
      "source": "remotive",
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
| `REFRESH_INTERVAL_SECONDS` | `21600` | Background refresh interval |
| `SOURCE_TIMEOUT_SECONDS` | `15` | Per-source HTTP timeout |
| `MAX_LIMIT` | `100` | Maximum `GET /jobs` page size |
| `DEFAULT_LIMIT` | `25` | Default `GET /jobs` page size |
| `ENABLED_SOURCES` | `remotive,remoteok` | Comma-separated source list |
| `REFRESH_ON_STARTUP` | `true` | Start a background refresh on boot |
| `ENABLE_BACKGROUND_REFRESH` | `true` | Enable scheduled refresh loop |
| `ADMIN_REFRESH_TOKEN` | unset | Protects `POST /refresh` |
| `CORS_ORIGINS` | `*` | CORS origin policy |

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

If your hosting provider runs multiple Gunicorn workers, use one of these
patterns:

- Keep `REFRESH_ON_STARTUP=true` and `ENABLE_BACKGROUND_REFRESH=false`, then call
  `POST /refresh` from an external scheduler every 6 hours.
- Or run a single worker for this small API and keep background refresh enabled.

## RapidAPI Listing Copy

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

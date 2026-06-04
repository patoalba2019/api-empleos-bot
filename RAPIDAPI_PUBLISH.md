# RapidAPI Publish Checklist

Use this file to configure the RapidAPI Studio listing for RemoteJobsAPI. Keep
pricing plans unchanged unless you intentionally update them later.

## General

API name:

```text
RemoteJobsAPI
```

Logo:

```text
assets/remotejobs-api-logo-500.png
```

Category:

```text
Jobs
```

Short description:

```text
Normalized remote job listings from public job-board feeds, with search, filters, pagination, stats, and source attribution.
```

Long description:

```markdown
RemoteJobsAPI gives developers one clean feed of remote jobs aggregated from public job-board sources.

It normalizes different source formats into one contract, deduplicates listings, cleans noisy descriptions, repairs common encoding issues, supports accent-insensitive search, and exposes production-friendly filtering and pagination.

Use it to power job boards, recruiting dashboards, AI agents, no-code automations, market research tools, career apps, and lead-generation workflows without maintaining multiple job-source parsers.

### What you get

- Fresh remote job listings from Remote OK and Himalayas
- Search across title, company, location, category, tags, and description
- Filters by company, location, category, tag, and source
- Pagination with `limit` and `offset`
- Individual job detail by id
- Job statistics by source, category, and location
- Source metadata and attribution
- Persistent cache so clients can keep receiving the last successful snapshot if an upstream source is temporarily unavailable

### Data transparency

Every job includes `url`, `source`, and `source_domain` so users can apply through the original job posting. Source attribution is included in API metadata.
```

Suggested tags:

```text
remote jobs, jobs api, hiring, recruitment, developer jobs, latam jobs, work from home, job search, careers, remote work
```

## Definitions

Recommended source of truth:

```text
openapi.yaml
```

RapidAPI recommends updating an API version by uploading an OpenAPI document so
manual listing and endpoint changes do not drift out of sync. Upload the
repository `openapi.yaml` in Hub Listing > Definitions > API Specs.

Important: before uploading, replace the placeholder server URL:

```yaml
servers:
  - url: https://YOUR_DEPLOYED_HOST
```

with the production host RapidAPI should proxy to.

## Main Endpoints

### `GET /jobs`

Best demo request:

```text
/jobs?q=python&location=latam&limit=10
```

Endpoint description:

```text
Search normalized remote job listings. Supports full-text search, company, location, category, tag, source, sorting, pagination, and optional full descriptions.
```

### `GET /jobs/{job_id}`

Endpoint description:

```text
Returns a single normalized job listing by id, including the full cleaned description.
```

### `GET /stats`

Endpoint description:

```text
Returns total jobs, counts by source, top categories, and top locations.
```

### `GET /sources`

Endpoint description:

```text
Returns configured source feeds and attribution notes.
```

### `GET /health`

Endpoint description:

```text
Returns API health and cache metadata.
```

### `POST /refresh`

Endpoint description:

```text
Protected admin endpoint for refreshing the job cache. In production, set ADMIN_REFRESH_TOKEN and call it with Authorization: Bearer <token>.
```

Do not expose this endpoint as the main consumer-facing endpoint in RapidAPI
unless you intentionally want customers to trigger refreshes.

## Gateway

Set the Base URL to the deployed production host, not GitHub. RapidAPI proxies
requests to a running backend; it does not host the Python app from the repo.

Recommended production env vars:

```text
REQUIRE_PAID_GATEWAY=true
PAID_GATEWAY_SECRETS=<rapidapi-secret>,<zyla-secret>,<apimarket-secret>,<apyhub-secret>
REFRESH_ON_STARTUP=false
ENABLE_BACKGROUND_REFRESH=true
REFRESH_INTERVAL_SECONDS=21600
MAX_LIMIT=100
DEFAULT_LIMIT=25
ENABLED_SOURCES=remoteok,himalayas
HIMALAYAS_MAX_PAGES=5
CORS_ORIGINS=*
ADMIN_REFRESH_TOKEN=<secure-random-token>
```

Configure every paid marketplace gateway to send one of those secrets in a
private upstream header such as `X-API-Gateway-Secret`,
`X-RapidAPI-Proxy-Secret`, or `X-RemoteJobsAPI-Secret`. Do not publish the
Render URL as a customer-facing endpoint.

If your host runs multiple Gunicorn workers, use:

```text
ENABLE_BACKGROUND_REFRESH=false
```

and trigger `POST /refresh` from an external scheduler.

## Monetization

Recommended public plans:

- Basic evaluation: USD 0, 25 requests/month, hard limit.
- Pro: USD 9.99/month, 10,000 requests/month.
- Ultra: USD 29/month, 50,000 requests/month.
- Mega: USD 79/month, 200,000 requests/month.

The Basic plan is a controlled integration test, not a useful free production
plan. A buyer must be able to verify that the API returns real data before
paying. Direct backend access remains blocked by the gateway secret.

## Required Listing Improvements

- Add a spotlight linking to the public product page.
- Add one tutorial for building a remote-jobs search page.
- Add example responses for `/jobs`, `/stats`, and `/sources`.
- Keep source attribution visible in the listing and in every downstream app.
- Never describe delayed or cached feeds as real-time.

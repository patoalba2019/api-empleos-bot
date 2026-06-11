# RemoteJobsAPI

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/downloads/)
[![Flask](https://img.shields.io/badge/Flask-2.0%2B-green.svg)](https://flask.palletsprojects.com/)
[![License](https://img.shields.io/badge/License-Proprietary-red.svg)](LICENSE)
[![RapidAPI](https://img.shields.io/badge/RapidAPI-Paid-orange.svg)](https://rapidapi.com/patoalba2019/api/remotejobsapi)

![RemoteJobsAPI logo](assets/remotejobs-api-logo-500.png)

**🚀 Production-ready API for remote job listings with search, filters, and real-time aggregation**

[Subscribe on RapidAPI](https://rapidapi.com/patoalba2019/api/remotejobsapi?utm_source=github&utm_medium=repository&utm_campaign=remotejobs_readme) |
[View product details](https://patoapis-paid-apis.onrender.com/remote-jobs-api.html?utm_source=github&utm_medium=repository&utm_campaign=remotejobs_readme) |
[Live Demo](https://patoapis-paid-apis.onrender.com/)

> Commercial API access is paid and delivered through RapidAPI with
> marketplace-managed credentials.

## 🎯 Why RemoteJobsAPI?

**Stop building job scrapers. Start building products.**

RemoteJobsAPI is a production-ready Flask API that aggregates remote job listings from public job-board feeds and exposes them through one clean, normalized contract. It is designed for RapidAPI consumers who want fresh remote jobs without building source-specific parsers, deduplication, filtering, pagination, or cache logic themselves.

**Perfect for:**
- Job board websites
- Recruitment platforms
- Developer job aggregators
- AI-powered job matching
- Newsletter job feeds
- Mobile job applications

## Why it is useful

- Real remote-job data from public sources.
- Normalized response shape across multiple job boards.
- Search, filters, pagination, detail lookup, source metadata, and stats.
- Persistent cache designed to preserve the last successful snapshot during
  temporary source interruptions.
- Safe refresh behavior with optional admin token protection.
- Source attribution included for transparent downstream usage.

## 📡 Data Sources

The production configuration currently uses:

- **Jobicy**: `https://jobicy.com/api/v2/remote-jobs` - Fresh remote job listings
- **Himalayas**: `https://himalayas.app/jobs/api` - Curated remote opportunities

**Coming soon:**
- Remotive integration
- We Work Remotely integration
- RemoteOK integration

All sources require proper attribution. The API preserves original URLs and source fields for compliance.

Always keep the original `url`, `source`, and `source_domain` fields in consumer
apps so users can apply through the original job posting.

Both sources require attribution/link-back when their jobs are displayed. The
API preserves the original application URL and source fields so buyers can meet
those requirements. The commercial source mix focuses on Jobicy and Himalayas
for stable data and attribution. The production refresh interval is intentionally conservative: Jobicy
asks integrations to fetch only a few times per day, while Himalayas refreshes
its public data daily.

## 🛠️ API Endpoints

### `GET /`
API status, available endpoints, and current cache metadata.

**Response:**
```json
{
  "api": "RemoteJobsAPI",
  "version": "2.2.0",
  "endpoints": ["/", "/health", "/jobs", "/stats", "/sources"]
}
```

### `GET /health`
Lightweight health check for monitoring.

**Response:**
```json
{
  "status": "ok",
  "timestamp": "2026-06-07T23:00:00Z"
}
```

### `GET /jobs`
Returns normalized remote jobs with powerful filtering.

**Query Parameters:**

| Parameter | Description | Example |
|-----------|-------------|---------|
| `q` or `search` | Full-text search across title, company, location, tags | `python developer` |
| `company` | Filter by company name | `stripe` |
| `location` | Filter by location (supports "latam", "worldwide") | `latam` |
| `category` | Filter by category | `software` |
| `tag` | Filter by specific skill/technology | `react` |
| `source` | Filter by data source | `himalayas` |
| `limit` | Results per page (max 100) | `25` |
| `offset` | Pagination offset | `0` |
| `sort` | Sort order: `newest`, `company`, `title` | `newest` |
| `include_description` | Include full job description | `true` |

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
- `ALLOW_PUBLIC_REFRESH=true`: local-only testing escape hatch. Do not enable
  it on production deployments.

## ⚙️ Configuration

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
| `PAID_GATEWAY_SECRET_HASHES` | unset | Comma-separated SHA-256 hashes of authorized marketplace secrets |

## 🔒 Security & Production

### Paid Gateway Protection
The API uses marketplace gateway protection so authorized paying customers can
access job data through the configured marketplace flow:

- `/health` is public for uptime monitoring
- Job data endpoints require valid marketplace credentials
- Plaintext secrets and SHA-256 hashes are both supported
- Production requests are designed to use marketplace-managed credentials

### Local Development
Run local development with the same paid-gateway posture used in production.
Product data examples require a configured marketplace gateway secret.

## 🚀 Quick Start

### Installation
```bash
# Clone the repository
git clone https://github.com/patoalba2019/api-empleos-bot.git
cd api-empleos-bot

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the server
python server.py
```

### Test the API
```bash
# Health check
curl http://localhost:5000/health

# Get remote jobs
curl "http://localhost:5000/jobs?limit=10&q=python"

# Search by location
curl "http://localhost:5000/jobs?location=latam&limit=5"
```

## 🌐 Deployment

### Render (Recommended)
```bash
# Deploy with one click using the Render Blueprint
# The API is pre-configured for Render with:
# - Automatic HTTPS
# - Paid gateway protection
# - Health monitoring
# - Auto-scaling
```

### Docker
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["gunicorn", "server:app"]
```

### Environment Variables for Production
```bash
PORT=5000
REQUIRE_PAID_GATEWAY=true
PAID_GATEWAY_SECRET_HASHES=<your-hash>
ENABLED_SOURCES=jobicy,himalayas
REFRESH_INTERVAL_SECONDS=43200
```

## 📈 Pricing

### RapidAPI Plans
- **Starter**: $4.99/month - 1,000 requests/month
- **Pro**: $9.99/month - 10,000 requests/month  
- **Ultra**: $29/month - 50,000 requests/month
- **Mega**: $79/month - 200,000 requests/month

[Subscribe on RapidAPI](https://rapidapi.com/patoalba2019/api/remotejobsapi)

## 📊 Use Cases

- **Job Boards**: Power your remote job website with fresh listings
- **Recruitment Platforms**: Aggregate jobs for your ATS or recruiting tool
- **Mobile Apps**: Build job search applications
- **Newsletters**: Create automated job digest emails
- **AI Agents**: Feed job data to AI-powered job matching systems
- **Analytics**: Track remote job market trends

## 🤝 Contributing

This is a commercial API product. For feature requests or bug reports, please contact through RapidAPI or open an issue on GitHub.

## 📄 License

Proprietary software. All rights reserved. See [LICENSE](LICENSE).
Access to the hosted API requires an active paid RapidAPI subscription.

## 🔗 Links

- [RapidAPI Marketplace](https://rapidapi.com/patoalba2019/api/remotejobsapi)
- [Product Website](https://patoapis-paid-apis.onrender.com/remote-jobs-api.html)
- [Documentation](https://patoapis-paid-apis.onrender.com/guides/remote-jobs-search.html)
- [Support](https://rapidapi.com/patoalba2019/api/remotejobsapi/support)

## Recommended Marketplace Plans

- **Starter**: USD 4.99/month, 1,000 requests/month.
- **Pro**: USD 9.99/month, 10,000 requests/month.
- **Ultra**: USD 29/month, 50,000 requests/month.
- **Mega**: USD 79/month, 200,000 requests/month.

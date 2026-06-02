import hashlib
import html
import json
import os
import re
import threading
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests
from flask import Flask, jsonify, request


APP_NAME = "RemoteJobsAPI"
APP_VERSION = "2.0.0"
DATABASE_FILE = Path(os.environ.get("JOBS_DATABASE_FILE", "datos_empleos.json"))
REFRESH_INTERVAL_SECONDS = int(os.environ.get("REFRESH_INTERVAL_SECONDS", "21600"))
REQUEST_TIMEOUT_SECONDS = int(os.environ.get("SOURCE_TIMEOUT_SECONDS", "15"))
MAX_LIMIT = int(os.environ.get("MAX_LIMIT", "100"))
DEFAULT_LIMIT = int(os.environ.get("DEFAULT_LIMIT", "25"))
ENABLED_SOURCES = {
    source.strip().lower()
    for source in os.environ.get("ENABLED_SOURCES", "remotive,remoteok").split(",")
    if source.strip()
}
USER_AGENT = os.environ.get(
    "SOURCE_USER_AGENT",
    "RemoteJobsAPI/2.0 (+https://github.com/patoalba2019/api-empleos-bot)",
)


app = Flask(__name__)
CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*")


@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = CORS_ORIGINS
    response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response

cache_lock = threading.RLock()
refresh_lock = threading.Lock()
cache: dict[str, Any] = {
    "jobs": [],
    "metadata": {
        "api": APP_NAME,
        "version": APP_VERSION,
        "updated_at": None,
        "job_count": 0,
        "sources": [],
        "source_errors": {},
    },
}


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def parse_timestamp(value: Any) -> str | None:
    if value in (None, ""):
        return None

    if isinstance(value, (int, float)):
        timestamp = value / 1000 if value > 10_000_000_000 else value
        return datetime.fromtimestamp(timestamp, timezone.utc).replace(microsecond=0).isoformat()

    text = str(value).strip()
    if not text:
        return None

    formats = (
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%a, %d %b %Y %H:%M:%S %z",
    )
    normalized = text.replace("Z", "+00:00")
    for fmt in formats:
        try:
            parsed = datetime.strptime(normalized, fmt)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc).replace(microsecond=0).isoformat()
        except ValueError:
            continue

    try:
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).replace(microsecond=0).isoformat()
    except ValueError:
        return None


def strip_html(value: Any) -> str:
    if value is None:
        return ""
    text = re.sub(r"<[^>]+>", " ", str(value))
    text = html.unescape(text)
    text = repair_mojibake(text)
    return re.sub(r"\s+", " ", text).strip()


def repair_mojibake(text: str) -> str:
    if "Ã" not in text and "â" not in text:
        return text
    try:
        repaired = text.encode("latin1").decode("utf-8")
    except UnicodeError:
        return text
    return repaired if repaired.count("�") <= text.count("�") else text


def clean_description(value: Any) -> str:
    description = strip_html(value)
    description = re.sub(
        r"\s*Please mention the word \*\*.*?human\.\s*",
        " ",
        description,
        flags=re.IGNORECASE,
    )
    description = re.sub(
        r"\s*Please mention the word .*",
        " ",
        description,
        flags=re.IGNORECASE,
    )
    return re.sub(r"\s+", " ", description).strip()


def clean_location(value: Any) -> str:
    location = strip_html(value)
    return location.strip(" ,")


def search_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    without_accents = "".join(char for char in normalized if not unicodedata.combining(char))
    return without_accents.casefold()


def as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        raw_items = value
    elif isinstance(value, str):
        raw_items = re.split(r"[,;/|]", value)
    else:
        raw_items = [value]

    items: list[str] = []
    seen: set[str] = set()
    for item in raw_items:
        cleaned = strip_html(item)
        if cleaned and cleaned.lower() not in seen:
            seen.add(cleaned.lower())
            items.append(cleaned)
    return items


def stable_id(source: str, url: str, title: str, company: str) -> str:
    key = f"{source}|{url}|{title}|{company}".lower().encode("utf-8")
    return hashlib.sha1(key).hexdigest()[:16]


def source_domain(url: str) -> str | None:
    try:
        hostname = urlparse(url).hostname
        return hostname.replace("www.", "") if hostname else None
    except ValueError:
        return None


def normalize_job(raw_job: dict[str, Any], source: str) -> dict[str, Any] | None:
    if source == "remotive":
        url = raw_job.get("url") or raw_job.get("job_url") or ""
        title = strip_html(raw_job.get("title"))
        company = strip_html(raw_job.get("company_name"))
        description = clean_description(raw_job.get("description"))
        tags = as_list(raw_job.get("tags"))
        category = strip_html(raw_job.get("category"))
        location = clean_location(raw_job.get("candidate_required_location") or raw_job.get("location"))
        published_at = parse_timestamp(raw_job.get("publication_date"))
        salary = strip_html(raw_job.get("salary"))
    elif source == "remoteok":
        url = raw_job.get("url") or raw_job.get("apply_url") or ""
        title = strip_html(raw_job.get("position") or raw_job.get("title"))
        company = strip_html(raw_job.get("company"))
        description = clean_description(raw_job.get("description"))
        tags = as_list(raw_job.get("tags"))
        category = tags[0] if tags else ""
        location = clean_location(raw_job.get("location"))
        published_at = parse_timestamp(raw_job.get("date") or raw_job.get("epoch"))
        salary = normalize_salary(raw_job)
    else:
        return None

    if not title or not company or not url:
        return None

    job_id = stable_id(source, url, title, company)
    return {
        "id": job_id,
        "title": title,
        "company": company,
        "location": location or "Remote",
        "category": category or "Remote",
        "tags": tags,
        "salary": salary or None,
        "description": description,
        "url": url,
        "source": source,
        "source_domain": source_domain(url),
        "published_at": published_at,
        "remote": True,
    }


def normalize_salary(raw_job: dict[str, Any]) -> str | None:
    salary = strip_html(raw_job.get("salary"))
    if salary:
        return salary

    minimum = raw_job.get("salary_min")
    maximum = raw_job.get("salary_max")
    if minimum and maximum:
        return f"${minimum} - ${maximum}"
    if minimum:
        return f"From ${minimum}"
    if maximum:
        return f"Up to ${maximum}"
    return None


def fetch_json(url: str) -> Any:
    response = requests.get(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    if "charset" not in response.headers.get("content-type", "").lower():
        response.encoding = response.apparent_encoding or "utf-8"
    return response.json()


def fetch_remotive_jobs() -> list[dict[str, Any]]:
    payload = fetch_json("https://remotive.com/api/remote-jobs")
    jobs = payload.get("jobs", []) if isinstance(payload, dict) else []
    return [job for job in (normalize_job(item, "remotive") for item in jobs) if job]


def fetch_remoteok_jobs() -> list[dict[str, Any]]:
    payload = fetch_json("https://remoteok.com/api")
    jobs = payload[1:] if isinstance(payload, list) else []
    return [job for job in (normalize_job(item, "remoteok") for item in jobs) if job]


SOURCE_FETCHERS = {
    "remotive": fetch_remotive_jobs,
    "remoteok": fetch_remoteok_jobs,
}


def enabled_source_fetchers() -> dict[str, Any]:
    return {
        source_name: fetcher
        for source_name, fetcher in SOURCE_FETCHERS.items()
        if source_name in ENABLED_SOURCES
    }


def dedupe_jobs(jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    best_by_key: dict[str, dict[str, Any]] = {}
    for job in jobs:
        url_key = job["url"].split("?")[0].strip().lower()
        title_key = re.sub(r"\W+", "", job["title"].lower())
        company_key = re.sub(r"\W+", "", job["company"].lower())
        description_key = re.sub(r"\W+", "", job.get("description", "").lower())[:140]
        key = f"{title_key}:{company_key}:{description_key}" if description_key else url_key

        existing = best_by_key.get(key)
        if not existing or score_job(job) > score_job(existing):
            best_by_key[key] = job

    return sorted(best_by_key.values(), key=sort_date_key, reverse=True)


def score_job(job: dict[str, Any]) -> int:
    return sum(
        [
            20 if job.get("description") else 0,
            10 if job.get("salary") else 0,
            5 if job.get("tags") else 0,
            5 if job.get("published_at") else 0,
        ]
    )


def sort_date_key(job: dict[str, Any]) -> str:
    return job.get("published_at") or ""


def save_cache(snapshot: dict[str, Any]) -> None:
    temp_file = DATABASE_FILE.with_suffix(".tmp")
    with temp_file.open("w", encoding="utf-8") as file:
        json.dump(snapshot, file, ensure_ascii=False, indent=2)
    temp_file.replace(DATABASE_FILE)


def load_cache() -> None:
    global cache
    if not DATABASE_FILE.exists():
        save_cache(cache)
        return

    try:
        with DATABASE_FILE.open("r", encoding="utf-8") as file:
            loaded = json.load(file)
    except (OSError, json.JSONDecodeError):
        return

    if isinstance(loaded, list):
        loaded = {
            "jobs": loaded,
            "metadata": {
                "api": APP_NAME,
                "version": APP_VERSION,
                "updated_at": None,
                "job_count": len(loaded),
                "sources": [],
                "source_errors": {},
                "legacy_cache": True,
            },
        }

    if isinstance(loaded, dict) and isinstance(loaded.get("jobs"), list):
        with cache_lock:
            cache = loaded


def refresh_jobs() -> dict[str, Any]:
    if not refresh_lock.acquire(blocking=False):
        with cache_lock:
            return {
                "status": "already_running",
                "metadata": cache["metadata"],
            }

    try:
        collected: list[dict[str, Any]] = []
        source_errors: dict[str, str] = {}
        active_sources: list[str] = []

        for source_name, fetcher in enabled_source_fetchers().items():
            try:
                source_jobs = fetcher()
                collected.extend(source_jobs)
                active_sources.append(source_name)
            except requests.RequestException as exc:
                source_errors[source_name] = str(exc)
            except (ValueError, TypeError, KeyError) as exc:
                source_errors[source_name] = f"Invalid source payload: {exc}"

        if not collected:
            with cache_lock:
                metadata = cache["metadata"].copy()
                metadata["source_errors"] = source_errors
                metadata["last_refresh_attempt_at"] = now_iso()
                metadata["last_refresh_status"] = "failed"
                cache["metadata"] = metadata
                save_cache({"jobs": cache["jobs"], "metadata": metadata})
                return {
                    "status": "failed",
                    "message": "All job sources failed. Serving the last cached snapshot.",
                    "metadata": metadata,
                }

        jobs = dedupe_jobs(collected)
        snapshot = {
            "jobs": jobs,
            "metadata": {
                "api": APP_NAME,
                "version": APP_VERSION,
                "updated_at": now_iso(),
                "last_refresh_attempt_at": now_iso(),
                "last_refresh_status": "ok",
                "job_count": len(jobs),
                "sources": active_sources,
                "source_errors": source_errors,
                "refresh_interval_seconds": REFRESH_INTERVAL_SECONDS,
                "attribution": {
                    "remotive": "https://remotive.com",
                    "remoteok": "https://remoteok.com",
                },
            },
        }

        with cache_lock:
            cache.clear()
            cache.update(snapshot)
        save_cache(snapshot)
        return {"status": "ok", "metadata": snapshot["metadata"]}
    finally:
        refresh_lock.release()


def background_refresh_loop() -> None:
    while True:
        refresh_jobs()
        time.sleep(REFRESH_INTERVAL_SECONDS)


def query_bool(name: str, default: bool = False) -> bool:
    value = request.args.get(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "y"}


def parse_limit() -> tuple[int, int]:
    try:
        limit = int(request.args.get("limit", DEFAULT_LIMIT))
    except ValueError:
        limit = DEFAULT_LIMIT

    try:
        offset = int(request.args.get("offset", 0))
    except ValueError:
        offset = 0

    return max(1, min(limit, MAX_LIMIT)), max(0, offset)


def matches_filter(job: dict[str, Any], field: str, expected: str | None) -> bool:
    if not expected:
        return True
    expected_lower = search_text(expected)
    value = job.get(field)
    if isinstance(value, list):
        return any(expected_lower in search_text(str(item)) for item in value)
    return expected_lower in search_text(str(value or ""))


def filter_jobs(jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    q = request.args.get("q") or request.args.get("search")
    source = request.args.get("source")
    category = request.args.get("category")
    company = request.args.get("company")
    location = request.args.get("location")
    tag = request.args.get("tag")

    filtered: list[dict[str, Any]] = []
    for job in jobs:
        searchable_text = " ".join(
            [
                job.get("title", ""),
                job.get("company", ""),
                job.get("location", ""),
                job.get("category", ""),
                " ".join(job.get("tags", [])),
                job.get("description", ""),
            ]
        )

        if q and search_text(q) not in search_text(searchable_text):
            continue
        if not matches_filter(job, "source", source):
            continue
        if not matches_filter(job, "category", category):
            continue
        if not matches_filter(job, "company", company):
            continue
        if not matches_filter(job, "location", location):
            continue
        if not matches_filter(job, "tags", tag):
            continue
        filtered.append(job)

    sort = request.args.get("sort", "newest")
    if sort == "company":
        filtered.sort(key=lambda item: item.get("company", "").lower())
    elif sort == "title":
        filtered.sort(key=lambda item: item.get("title", "").lower())
    else:
        filtered.sort(key=sort_date_key, reverse=True)
    return filtered


def public_job(job: dict[str, Any], include_description: bool = False) -> dict[str, Any]:
    public = job.copy()
    if not include_description:
        public.pop("description", None)
    return public


@app.get("/")
def home():
    with cache_lock:
        metadata = cache["metadata"].copy()

    return jsonify(
        {
            "api": APP_NAME,
            "version": APP_VERSION,
            "status": "online",
            "description": "Normalized remote job listings from public job-board feeds.",
            "endpoints": {
                "jobs": "/jobs",
                "job_detail": "/jobs/<id>",
                "stats": "/stats",
                "sources": "/sources",
                "refresh": "/refresh",
            },
            "metadata": metadata,
        }
    )


@app.get("/health")
def health():
    with cache_lock:
        metadata = cache["metadata"].copy()
    status = "ok" if metadata.get("job_count", 0) > 0 else "degraded"
    return jsonify({"status": status, "metadata": metadata})


@app.get("/jobs")
def get_jobs():
    limit, offset = parse_limit()
    include_description = query_bool("include_description", False)

    with cache_lock:
        jobs = list(cache["jobs"])
        metadata = cache["metadata"].copy()

    if not jobs and not metadata.get("updated_at"):
        refresh_jobs()
        with cache_lock:
            jobs = list(cache["jobs"])
            metadata = cache["metadata"].copy()

    filtered = filter_jobs(jobs)
    paginated = filtered[offset : offset + limit]

    return jsonify(
        {
            "metadata": {
                **metadata,
                "total": len(filtered),
                "limit": limit,
                "offset": offset,
                "returned": len(paginated),
            },
            "jobs": [public_job(job, include_description) for job in paginated],
        }
    )


@app.get("/jobs/<job_id>")
def get_job(job_id: str):
    with cache_lock:
        jobs = list(cache["jobs"])

    for job in jobs:
        if job["id"] == job_id:
            return jsonify({"job": public_job(job, include_description=True)})
    return jsonify({"error": "Job not found", "id": job_id}), 404


@app.get("/stats")
def stats():
    with cache_lock:
        jobs = list(cache["jobs"])
        metadata = cache["metadata"].copy()

    by_source: dict[str, int] = {}
    by_category: dict[str, int] = {}
    by_location: dict[str, int] = {}
    for job in jobs:
        by_source[job["source"]] = by_source.get(job["source"], 0) + 1
        by_category[job["category"]] = by_category.get(job["category"], 0) + 1
        by_location[job["location"]] = by_location.get(job["location"], 0) + 1

    return jsonify(
        {
            "metadata": metadata,
            "total_jobs": len(jobs),
            "by_source": by_source,
            "top_categories": top_counts(by_category),
            "top_locations": top_counts(by_location),
        }
    )


@app.get("/sources")
def sources():
    return jsonify(
        {
            "sources": [
                {
                    "name": "remotive",
                    "url": "https://remotive.com/api/remote-jobs",
                    "attribution": "Jobs sourced from Remotive. Link back to the job URL.",
                },
                {
                    "name": "remoteok",
                    "url": "https://remoteok.com/api",
                    "attribution": "Jobs sourced from Remote OK. Link back to the job URL.",
                },
            ]
        }
    )


@app.post("/refresh")
def refresh():
    configured_token = os.environ.get("ADMIN_REFRESH_TOKEN")
    provided_token = request.headers.get("Authorization", "").replace("Bearer ", "").strip()
    public_refresh_enabled = os.environ.get("ALLOW_PUBLIC_REFRESH", "").lower() == "true"

    if configured_token and provided_token != configured_token:
        return jsonify({"error": "Invalid refresh token"}), 401
    if not configured_token and not public_refresh_enabled:
        return (
            jsonify(
                {
                    "error": "Manual refresh is disabled",
                    "hint": "Set ADMIN_REFRESH_TOKEN or ALLOW_PUBLIC_REFRESH=true to enable this endpoint.",
                }
            ),
            403,
        )

    result = refresh_jobs()
    status_code = 200 if result["status"] in {"ok", "already_running"} else 503
    return jsonify(result), status_code


def top_counts(counts: dict[str, int], limit: int = 10) -> list[dict[str, Any]]:
    ordered = sorted(counts.items(), key=lambda item: item[1], reverse=True)
    return [{"name": name, "count": count} for name, count in ordered[:limit]]


def should_start_background_thread() -> bool:
    if os.environ.get("ENABLE_BACKGROUND_REFRESH", "true").lower() != "true":
        return False
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        return True
    if "gunicorn" in os.environ.get("SERVER_SOFTWARE", "").lower():
        return os.environ.get("RUN_REFRESH_IN_GUNICORN", "false").lower() == "true"
    return os.environ.get("WERKZEUG_RUN_MAIN") is None


load_cache()

if os.environ.get("REFRESH_ON_STARTUP", "false").lower() == "true":
    threading.Thread(target=refresh_jobs, daemon=True).start()

if should_start_background_thread():
    threading.Thread(target=background_refresh_loop, daemon=True).start()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

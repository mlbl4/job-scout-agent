import hashlib
import json
import logging
import time
from pathlib import Path
from typing import Any, Callable

import httpx
from langchain_core.tools import tool

from . import config
from .models import Job

logger = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).resolve().parents[2] / ".cache"
CACHE_TTL_SECONDS = 24 * 60 * 60
_HTTP_TIMEOUT = 20.0


def _clip(text: Any, limit: int = 1500) -> str:
    return str(text or "")[:limit]


def _cache_path(source: str, args: dict[str, Any]) -> Path:
    payload = json.dumps({"source": source, "args": args}, sort_keys=True)
    digest = hashlib.sha256(payload.encode()).hexdigest()
    return CACHE_DIR / f"{digest}.json"


def _read_cache(path: Path) -> list[Job] | None:
    if not path.exists() or time.time() - path.stat().st_mtime >= CACHE_TTL_SECONDS:
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return [Job.model_validate(item) for item in raw]
    except Exception:
        logger.exception("Failed to read cache %s", path)
        return None


def _write_cache(path: Path, jobs: list[Job]) -> None:
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps([job.model_dump() for job in jobs], ensure_ascii=False),
            encoding="utf-8",
        )
    except Exception:
        logger.exception("Failed to write cache %s", path)


def _cached(source: str, args: dict[str, Any], fetch: Callable[[], list[Job]]) -> list[Job]:
    path = _cache_path(source, args)
    cached = _read_cache(path)
    if cached is not None:
        return cached
    try:
        jobs = fetch()
    except Exception:
        logger.exception("%s search failed", source)
        return []
    _write_cache(path, jobs)
    return jobs


def search_jsearch(query: str, location: str, remote_only: bool) -> list[Job]:
    def fetch() -> list[Job]:
        response = httpx.get(
            "https://jsearch.p.rapidapi.com/search",
            headers={
                "X-RapidAPI-Key": config.RAPIDAPI_KEY or "",
                "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
            },
            params={
                "query": f"{query} in {location}",
                "country": "es",
                "date_posted": "month",
                "num_pages": 1,
                "work_from_home": remote_only,
            },
            timeout=_HTTP_TIMEOUT,
        )
        response.raise_for_status()
        jobs: list[Job] = []
        for item in response.json().get("data") or []:
            loc_parts = [item.get("job_city"), item.get("job_state"), item.get("job_country")]
            location_str = ", ".join(p for p in loc_parts if p) or location
            jobs.append(
                Job(
                    id=str(item.get("job_id") or ""),
                    title=item.get("job_title") or "",
                    company=item.get("employer_name") or "",
                    location=location_str,
                    description=_clip(item.get("job_description")),
                    url=item.get("job_apply_link") or item.get("job_google_link") or "",
                    source="jsearch",
                    remote_ok=bool(item.get("job_is_remote")),
                    posted_at=item.get("job_posted_at_datetime_utc"),
                )
            )
        return jobs

    return _cached("jsearch", {"query": query, "location": location, "remote_only": remote_only}, fetch)


def search_adzuna(query: str, location: str) -> list[Job]:
    def fetch() -> list[Job]:
        response = httpx.get(
            "https://api.adzuna.com/v1/api/jobs/es/search/1",
            params={
                "app_id": config.ADZUNA_APP_ID or "",
                "app_key": config.ADZUNA_APP_KEY or "",
                "what": query,
                "where": location,
                "results_per_page": 20,
                "max_days_old": 30,
            },
            timeout=_HTTP_TIMEOUT,
        )
        response.raise_for_status()
        jobs: list[Job] = []
        for item in response.json().get("results") or []:
            loc = (item.get("location") or {}).get("display_name") or location
            desc = item.get("description") or ""
            jobs.append(
                Job(
                    id=str(item.get("id") or ""),
                    title=item.get("title") or "",
                    company=(item.get("company") or {}).get("display_name") or "",
                    location=loc,
                    description=_clip(desc),
                    url=item.get("redirect_url") or "",
                    source="adzuna",
                    remote_ok="remote" in f"{loc} {desc}".lower(),
                    posted_at=item.get("created"),
                )
            )
        return jobs

    return _cached("adzuna", {"query": query, "location": location}, fetch)


def search_remotive(query: str) -> list[Job]:
    def fetch() -> list[Job]:
        response = httpx.get(
            "https://remotive.com/api/remote-jobs",
            params={"search": query, "limit": 20},
            timeout=_HTTP_TIMEOUT,
        )
        response.raise_for_status()
        jobs: list[Job] = []
        for item in response.json().get("jobs") or []:
            jobs.append(
                Job(
                    id=str(item.get("id") or ""),
                    title=item.get("title") or "",
                    company=item.get("company_name") or "",
                    location=item.get("candidate_required_location") or "Remote",
                    description=_clip(item.get("description")),
                    url=item.get("url") or "",
                    source="remotive",
                    remote_ok=True,
                    posted_at=item.get("publication_date"),
                )
            )
        return jobs

    return _cached("remotive", {"query": query}, fetch)


def _dedupe(jobs: list[Job]) -> list[Job]:
    seen: set[tuple[str, str]] = set()
    unique: list[Job] = []
    for job in jobs:
        key = (job.title.strip().lower(), job.company.strip().lower())
        if key in seen:
            continue
        seen.add(key)
        unique.append(job)
    return unique


def search_jobs(query: str, location: str = "Spain", remote_only: bool = False) -> list[Job]:
    jobs = search_jsearch(query, location, remote_only)
    if len(jobs) < 5:
        jobs = jobs + search_adzuna(query, location)
    if remote_only:
        jobs = jobs + search_remotive(query)
    return _dedupe(jobs)


@tool
def search_jobs_tool(query: str, location: str = "Spain", remote_only: bool = False) -> list[dict]:
    """Search job boards (JSearch, then Adzuna if needed, plus Remotive when remote-only).

    Args:
        query: Job title or keywords to search for (e.g. "data engineer").
        location: City or country to search in (e.g. "Alicante" or "Spain").
        remote_only: If True, prefer remote roles (JSearch work_from_home) and also query Remotive.
    """
    return [job.model_dump() for job in search_jobs(query, location, remote_only)]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    for job in search_jobs("data engineer", "Alicante"):
        print(f"{job.title} | {job.company} | {job.location} | {job.source}")

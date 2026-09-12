#!/usr/bin/env python3
"""Machine-readable client for the official Yargitay decision search website.

The website endpoints used here are public but undocumented.  Keep HTTP and
response-shape concerns in this module; legal analysis belongs to the agent.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import random
import re
import socket
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from html.parser import HTMLParser
from http.cookiejar import CookieJar
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol, Sequence

BASE_URL = "https://karararama.yargitay.gov.tr"
SEARCH_PATH = "/aramadetaylist"
DOCUMENT_PATH = "/getDokuman"
DEFAULT_TIMEOUT = 30.0
DEFAULT_MIN_INTERVAL = 3.0
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100
DEFAULT_MAX_RESULTS = 100
DEFAULT_MAX_PAGES = 50
CACHE_VERSION = 1
USER_AGENT = "yargitay-research-skill/1.0 (+public legal research client)"


class YargitayError(Exception):
    """Expected client error that can be represented as stable JSON."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        retryable: bool = False,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable
        self.details = dict(details or {})

    def as_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "code": self.code,
            "message": self.message,
            "retryable": self.retryable,
        }
        if self.details:
            result["details"] = self.details
        return result


class JsonArgumentParser(argparse.ArgumentParser):
    """Route invalid CLI input through the machine-readable error contract."""

    def error(self, message: str) -> None:
        raise YargitayError("invalid_arguments", message)


class Transport(Protocol):
    def request_json(
        self,
        method: str,
        path: str,
        *,
        payload: Mapping[str, Any] | None = None,
        params: Mapping[str, str] | None = None,
    ) -> Mapping[str, Any]: ...


@dataclass(frozen=True)
class ClientConfig:
    base_url: str = BASE_URL
    timeout: float = DEFAULT_TIMEOUT
    min_interval: float = DEFAULT_MIN_INTERVAL
    max_retries: int = 2
    retry_base: float = 5.0


class UrlLibTransport:
    """Small stateful HTTP transport with cookies, throttling, and bounded retry."""

    def __init__(
        self,
        config: ClientConfig,
        *,
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
        opener: Any | None = None,
    ) -> None:
        self.config = config
        self._sleep = sleep
        self._monotonic = monotonic
        self._last_request_at: float | None = None
        self._bootstrapped = False
        self._opener = opener or urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(CookieJar())
        )

    def request_json(
        self,
        method: str,
        path: str,
        *,
        payload: Mapping[str, Any] | None = None,
        params: Mapping[str, str] | None = None,
    ) -> Mapping[str, Any]:
        self._bootstrap_session()
        url = self._build_url(path, params)
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = urllib.request.Request(
            url,
            data=body,
            method=method,
            headers=self._headers(has_body=body is not None),
        )

        for attempt in range(self.config.max_retries + 1):
            self._throttle()
            try:
                with self._opener.open(request, timeout=self.config.timeout) as response:
                    raw = response.read()
                    content_type = response.headers.get("Content-Type", "")
                    if self._looks_rate_limited(response.status, content_type, raw):
                        raise YargitayError(
                            "rate_limited",
                            "The official Yargitay website applied an access limit.",
                            retryable=True,
                            details={"status": response.status},
                        )
                    return self._decode_json(raw, response.status, content_type)
            except urllib.error.HTTPError as exc:
                raw = exc.read()
                if exc.code == 429:
                    error = YargitayError(
                        "rate_limited",
                        "The official Yargitay website applied an access limit.",
                        retryable=True,
                        details={"status": exc.code},
                    )
                    retry_after = _parse_retry_after(exc.headers.get("Retry-After"))
                elif 500 <= exc.code < 600:
                    error = YargitayError(
                        "upstream_error",
                        "The official Yargitay website returned a server error.",
                        retryable=True,
                        details={"status": exc.code},
                    )
                    retry_after = None
                else:
                    raise YargitayError(
                        "http_error",
                        "The official Yargitay website rejected the request.",
                        details={"status": exc.code, "response": _safe_excerpt(raw)},
                    ) from exc
            except YargitayError as exc:
                error = exc
                retry_after = None
            except (urllib.error.URLError, TimeoutError, socket.timeout) as exc:
                error = YargitayError(
                    "network_error",
                    "Could not reach the official Yargitay website.",
                    retryable=True,
                    details={"reason": str(getattr(exc, "reason", exc))},
                )
                retry_after = None

            if not error.retryable or attempt >= self.config.max_retries:
                raise error
            self._sleep(retry_after or self._backoff(attempt))

        raise AssertionError("unreachable")

    def _bootstrap_session(self) -> None:
        if self._bootstrapped:
            return
        request = urllib.request.Request(
            self.config.base_url.rstrip("/") + "/index",
            headers=self._headers(has_body=False),
        )
        try:
            with self._opener.open(request, timeout=self.config.timeout) as response:
                response.read(1)
        except (urllib.error.URLError, TimeoutError, socket.timeout):
            # The API often works without the initial cookie. Let the real request
            # produce the actionable error and participate in retry handling.
            pass
        self._bootstrapped = True

    def _headers(self, *, has_body: bool) -> dict[str, str]:
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Origin": self.config.base_url,
            "Referer": self.config.base_url.rstrip("/") + "/index",
            "User-Agent": USER_AGENT,
            "X-Requested-With": "XMLHttpRequest",
        }
        if has_body:
            headers["Content-Type"] = "application/json; charset=UTF-8"
        return headers

    def _build_url(
        self, path: str, params: Mapping[str, str] | None
    ) -> str:
        url = self.config.base_url.rstrip("/") + "/" + path.lstrip("/")
        return url if not params else url + "?" + urllib.parse.urlencode(params)

    def _throttle(self) -> None:
        if self._last_request_at is not None:
            elapsed = self._monotonic() - self._last_request_at
            if elapsed < self.config.min_interval:
                self._sleep(self.config.min_interval - elapsed)
        self._last_request_at = self._monotonic()

    def _backoff(self, attempt: int) -> float:
        base = self.config.retry_base * (2**attempt)
        return base + random.uniform(0, min(1.0, base * 0.1))

    @staticmethod
    def _looks_rate_limited(status: int, content_type: str, raw: bytes) -> bool:
        if status == 429:
            return True
        if "html" not in content_type.lower():
            return False
        excerpt = raw[:4000].decode("utf-8", "replace").casefold()
        return "erişim sınırı" in excerpt or "erisim siniri" in excerpt

    @staticmethod
    def _decode_json(raw: bytes, status: int, content_type: str) -> Mapping[str, Any]:
        try:
            value = json.loads(raw.decode("utf-8-sig"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise YargitayError(
                "invalid_response",
                "The official endpoint returned a non-JSON response.",
                details={
                    "status": status,
                    "content_type": content_type,
                    "response": _safe_excerpt(raw),
                },
            ) from exc
        if not isinstance(value, dict):
            raise YargitayError(
                "schema_changed",
                "The official endpoint response root is not an object.",
            )
        return value


class DecisionHtmlParser(HTMLParser):
    """Convert decision HTML into readable text without third-party packages."""

    BLOCK_TAGS = {
        "address", "article", "aside", "blockquote", "br", "div", "footer",
        "h1", "h2", "h3", "h4", "h5", "h6", "header", "hr", "li", "main",
        "ol", "p", "pre", "section", "table", "td", "th", "tr", "ul",
    }

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._ignored_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style"}:
            self._ignored_depth += 1
        elif not self._ignored_depth and tag in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"} and self._ignored_depth:
            self._ignored_depth -= 1
        elif not self._ignored_depth and tag in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._ignored_depth:
            self.parts.append(data)

    def text(self) -> str:
        value = html.unescape("".join(self.parts)).replace("\xa0", " ")
        value = re.sub(r"[ \t\f\v]+", " ", value)
        value = re.sub(r" *\n *", "\n", value)
        value = re.sub(r"\n{3,}", "\n\n", value)
        return value.strip()


@dataclass
class DocumentCache:
    directory: Path | None

    def get(self, document_id: str) -> Mapping[str, Any] | None:
        if self.directory is None:
            return None
        path = self.directory / f"{document_id}.json"
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        if not isinstance(value, dict) or value.get("cache_version") != CACHE_VERSION:
            return None
        return value

    def put(self, document_id: str, value: Mapping[str, Any]) -> bool:
        if self.directory is None:
            return False
        temporary_name: str | None = None
        try:
            self.directory.mkdir(parents=True, exist_ok=True)
            destination = self.directory / f"{document_id}.json"
            fd, temporary_name = tempfile.mkstemp(
                prefix=f".{document_id}.", suffix=".tmp", dir=self.directory
            )
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
                json.dump(value, stream, ensure_ascii=False, separators=(",", ":"))
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary_name, destination)
            return True
        except OSError:
            if temporary_name is not None:
                try:
                    os.unlink(temporary_name)
                except OSError:
                    pass
            return False


@dataclass(frozen=True)
class SearchCriteria:
    query: str = ""
    chamber: str = ""
    case_year: str = ""
    case_first: str = ""
    case_last: str = ""
    decision_year: str = ""
    decision_first: str = ""
    decision_last: str = ""
    date_from: str = ""
    date_to: str = ""

    def validate(self) -> None:
        values = [
            self.query, self.chamber, self.case_year, self.case_first,
            self.case_last, self.decision_year, self.decision_first,
            self.decision_last, self.date_from, self.date_to,
        ]
        if not any(value.strip() for value in values):
            raise YargitayError(
                "invalid_arguments", "Provide a query or at least one search filter."
            )
        for name, value in (("date_from", self.date_from), ("date_to", self.date_to)):
            if value:
                if not re.fullmatch(r"\d{2}\.\d{2}\.\d{4}", value):
                    raise YargitayError(
                        "invalid_arguments", f"{name} must use DD.MM.YYYY."
                    )
                try:
                    datetime.strptime(value, "%d.%m.%Y")
                except ValueError as exc:
                    raise YargitayError(
                        "invalid_arguments", f"{name} must use DD.MM.YYYY."
                    ) from exc
        if self.date_from and self.date_to:
            start = datetime.strptime(self.date_from, "%d.%m.%Y")
            end = datetime.strptime(self.date_to, "%d.%m.%Y")
            if start > end:
                raise YargitayError(
                    "invalid_arguments", "date_from cannot be later than date_to."
                )
        for name, value in (("case_year", self.case_year), ("decision_year", self.decision_year)):
            if value and not re.fullmatch(r"\d{4}", value):
                raise YargitayError(
                    "invalid_arguments", f"{name} must be a four-digit year."
                )
        sequence_fields = (
            ("case_first", self.case_first),
            ("case_last", self.case_last),
            ("decision_first", self.decision_first),
            ("decision_last", self.decision_last),
        )
        for name, value in sequence_fields:
            if value and not value.isdigit():
                raise YargitayError(
                    "invalid_arguments", f"{name} must contain digits only."
                )
        _validate_number_range(
            "case", self.case_year, self.case_first, self.case_last
        )
        _validate_number_range(
            "decision", self.decision_year, self.decision_first, self.decision_last
        )

    def api_fields(self) -> dict[str, Any]:
        fields: dict[str, Any] = {
            "aranan": self.query,
            "arananKelime": self.query,
        }
        chamber = "" if self.chamber.strip().upper() == "ALL" else self.chamber
        optional = {
            "birimYrgKurulDaire": chamber,
            "esasYil": self.case_year,
            "esasIlkSiraNo": self.case_first,
            "esasSonSiraNo": self.case_last,
            "kararYil": self.decision_year,
            "kararIlkSiraNo": self.decision_first,
            "kararSonSiraNo": self.decision_last,
            "baslangicTarihi": self.date_from,
            "bitisTarihi": self.date_to,
        }
        fields.update({key: value for key, value in optional.items() if value})
        return fields

    def public_filters(self) -> dict[str, str]:
        chamber = "" if self.chamber.strip().upper() == "ALL" else self.chamber
        return {
            key: value
            for key, value in {
                "chamber": chamber,
                "case_year": self.case_year,
                "case_first": self.case_first,
                "case_last": self.case_last,
                "decision_year": self.decision_year,
                "decision_first": self.decision_first,
                "decision_last": self.decision_last,
                "date_from": self.date_from,
                "date_to": self.date_to,
            }.items()
            if value
        }


@dataclass
class YargitayClient:
    transport: Transport
    cache: DocumentCache = field(default_factory=lambda: DocumentCache(None))
    base_url: str = BASE_URL

    def health(self) -> dict[str, Any]:
        criteria = SearchCriteria(query='"__yargitay_skill_healthcheck__"')
        result = self.search(criteria, page=1, page_size=1)
        return {
            "ok": True,
            "source": "yargitay",
            "status": "compatible",
            "official_base_url": self.base_url,
            "search_endpoint": SEARCH_PATH,
            "checked_at": _utc_now(),
            "response_schema_valid": result["total"] >= 0,
        }

    def search(
        self, criteria: SearchCriteria, *, page: int, page_size: int
    ) -> dict[str, Any]:
        criteria.validate()
        _validate_pagination(page, page_size)
        request_data = criteria.api_fields()
        request_data.update({"pageSize": page_size, "pageNumber": page})
        response = self.transport.request_json(
            "POST", SEARCH_PATH, payload={"data": request_data}
        )
        inner = _require_mapping(response.get("data"), "data")
        rows = inner.get("data")
        total = inner.get("recordsTotal")
        if not isinstance(rows, list) or not isinstance(total, int):
            raise YargitayError(
                "schema_changed",
                "The official search response no longer has the expected schema.",
                details={"expected": "data.data[] and data.recordsTotal"},
            )
        results = [_normalize_result(row, self.base_url) for row in rows]
        return {
            "ok": True,
            "source": "yargitay",
            "official_base_url": self.base_url,
            "query": criteria.query,
            "filters": criteria.public_filters(),
            "page": page,
            "page_size": page_size,
            "total": total,
            "has_more": page * page_size < total,
            "results": results,
        }

    def search_all(
        self,
        criteria: SearchCriteria,
        *,
        page_size: int,
        max_results: int,
        max_pages: int = DEFAULT_MAX_PAGES,
    ) -> dict[str, Any]:
        if max_results < 1:
            raise YargitayError(
                "invalid_arguments", "max_results must be at least 1."
            )
        if max_pages < 1:
            raise YargitayError(
                "invalid_arguments", "max_pages must be at least 1."
            )
        _validate_pagination(1, page_size)
        results: list[dict[str, Any]] = []
        seen: set[str] = set()
        page = 1
        pages_fetched = 0
        total = 0

        stop_reason = "result_limit"
        while len(results) < max_results and page <= max_pages:
            batch = self.search(criteria, page=page, page_size=page_size)
            pages_fetched += 1
            total = batch["total"]
            rows = batch["results"]
            for row in rows:
                document_id = row["id"]
                if document_id not in seen:
                    seen.add(document_id)
                    results.append(row)
                    if len(results) >= max_results:
                        break
            if not rows or not batch["has_more"]:
                stop_reason = "no_results" if not rows else "source_exhausted"
                break
            page += 1
        else:
            if page > max_pages:
                stop_reason = "page_limit"

        return {
            "ok": True,
            "source": "yargitay",
            "official_base_url": self.base_url,
            "query": criteria.query,
            "filters": criteria.public_filters(),
            "total": total,
            "returned": len(results),
            "pages_fetched": pages_fetched,
            "max_results": max_results,
            "max_pages": max_pages,
            "truncated": len(results) < total,
            "stop_reason": stop_reason,
            "results": results,
        }

    def get_document(self, document_id: str, *, refresh: bool = False) -> dict[str, Any]:
        if not re.fullmatch(r"\d+", document_id):
            raise YargitayError(
                "invalid_arguments", "document_id must contain digits only."
            )
        if not refresh:
            cached = self.cache.get(document_id)
            if cached is not None:
                result = dict(cached)
                result["cache"] = "hit"
                return result

        response = self.transport.request_json(
            "GET", DOCUMENT_PATH, params={"id": document_id}
        )
        document_html = response.get("data")
        if not isinstance(document_html, str):
            raise YargitayError(
                "schema_changed",
                "The official document response no longer contains HTML in data.",
            )
        parser = DecisionHtmlParser()
        parser.feed(document_html)
        text = parser.text()
        if not text:
            raise YargitayError(
                "document_not_found",
                "The official source returned no decision text for this document ID.",
                details={"document_id": document_id},
            )
        result: dict[str, Any] = {
            "cache_version": CACHE_VERSION,
            "ok": True,
            "source": "yargitay",
            "document_id": document_id,
            "official_source_url": _document_url(self.base_url, document_id),
            "retrieved_at": _utc_now(),
            "official_source_retrieved": True,
            "text": text,
        }
        cache_written = self.cache.put(document_id, result)
        result["cache"] = "miss" if cache_written else "disabled_or_write_failed"
        return result


def _normalize_result(row: Any, base_url: str) -> dict[str, Any]:
    if not isinstance(row, dict):
        raise YargitayError("schema_changed", "A search result is not an object.")
    document_id = str(row.get("id", "")).strip()
    if not document_id:
        raise YargitayError("schema_changed", "A search result has no document ID.")
    raw_date = _optional_string(row.get("kararTarihi"))
    return {
        "id": document_id,
        "daire": _optional_string(row.get("daire")),
        "esas_no": _optional_string(row.get("esasNo")),
        "karar_no": _optional_string(row.get("kararNo")),
        "karar_tarihi": raw_date,
        "karar_tarihi_iso": _date_to_iso(raw_date),
        "official_source_url": _document_url(base_url, document_id),
    }


def _optional_string(value: Any) -> str | None:
    return None if value is None else str(value).strip() or None


def _date_to_iso(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%d.%m.%Y").date().isoformat()
    except ValueError:
        return None


def _document_url(base_url: str, document_id: str) -> str:
    query = urllib.parse.urlencode({"id": document_id})
    return f"{base_url.rstrip('/')}{DOCUMENT_PATH}?{query}"


def _require_mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise YargitayError(
            "schema_changed", f"The official response field {name!r} is not an object."
        )
    return value


def _validate_pagination(page: int, page_size: int) -> None:
    if page < 1:
        raise YargitayError("invalid_arguments", "page must be at least 1.")
    if not 1 <= page_size <= MAX_PAGE_SIZE:
        raise YargitayError(
            "invalid_arguments", f"page_size must be between 1 and {MAX_PAGE_SIZE}."
        )


def _validate_number_range(
    name: str, year: str, first: str, last: str
) -> None:
    values = (year, first, last)
    if any(values) and not all(values):
        raise YargitayError(
            "invalid_arguments",
            f"{name} filtering requires year, first, and last together.",
        )
    if first and last and int(first) > int(last):
        raise YargitayError(
            "invalid_arguments", f"{name}_first cannot be greater than {name}_last."
        )


def _parse_retry_after(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        return None


def _safe_excerpt(raw: bytes, limit: int = 500) -> str:
    return raw[:limit].decode("utf-8", "replace").replace("\x00", "")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def default_cache_dir() -> Path:
    override = os.environ.get("YARGITAY_CACHE_DIR")
    if override:
        return Path(override).expanduser()
    if os.name == "nt" and os.environ.get("LOCALAPPDATA"):
        return Path(os.environ["LOCALAPPDATA"]) / "yargitay-research"
    xdg = os.environ.get("XDG_CACHE_HOME")
    if xdg:
        return Path(xdg) / "yargitay-research"
    return Path.home() / ".cache" / "yargitay-research"


def build_parser() -> argparse.ArgumentParser:
    parser = JsonArgumentParser(
        description="Search and retrieve decisions from the official Yargitay website."
    )
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    parser.add_argument("--min-interval", type=float, default=DEFAULT_MIN_INTERVAL)
    parser.add_argument("--max-retries", type=int, default=2)
    parser.add_argument("--retry-base", type=float, default=5.0)
    parser.add_argument("--cache-dir", type=Path, default=default_cache_dir())
    parser.add_argument("--no-cache", action="store_true")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("health", help="Check endpoint reachability and schema compatibility.")

    search = subparsers.add_parser("search", help="Fetch one search result page.")
    _add_search_arguments(search)
    search.add_argument("--page", type=int, default=1)
    search.add_argument("--page-size", type=int, default=DEFAULT_PAGE_SIZE)

    search_all = subparsers.add_parser("search-all", help="Fetch bounded, deduplicated pages.")
    _add_search_arguments(search_all)
    search_all.add_argument("--page-size", type=int, default=DEFAULT_PAGE_SIZE)
    search_all.add_argument("--max-results", type=int, default=DEFAULT_MAX_RESULTS)
    search_all.add_argument("--max-pages", type=int, default=DEFAULT_MAX_PAGES)

    get = subparsers.add_parser("get", help="Retrieve an official decision full text.")
    get.add_argument("document_id")
    get.add_argument("--refresh", action="store_true")
    return parser


def _add_search_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--query", default="")
    parser.add_argument("--chamber", default="")
    parser.add_argument("--case-year", default="")
    parser.add_argument("--case-first", default="")
    parser.add_argument("--case-last", default="")
    parser.add_argument("--decision-year", default="")
    parser.add_argument("--decision-first", default="")
    parser.add_argument("--decision-last", default="")
    parser.add_argument("--date-from", default="")
    parser.add_argument("--date-to", default="")


def _criteria_from_args(args: argparse.Namespace) -> SearchCriteria:
    return SearchCriteria(
        query=args.query,
        chamber=args.chamber,
        case_year=args.case_year,
        case_first=args.case_first,
        case_last=args.case_last,
        decision_year=args.decision_year,
        decision_first=args.decision_first,
        decision_last=args.decision_last,
        date_from=args.date_from,
        date_to=args.date_to,
    )


def run(args: argparse.Namespace) -> dict[str, Any]:
    if (
        args.timeout <= 0
        or args.min_interval < 0
        or args.max_retries < 0
        or args.retry_base < 0
    ):
        raise YargitayError(
            "invalid_arguments",
            "timeout must be positive; intervals, retry counts, and retry base "
            "cannot be negative.",
        )
    config = ClientConfig(
        timeout=args.timeout,
        min_interval=args.min_interval,
        max_retries=args.max_retries,
        retry_base=args.retry_base,
    )
    cache = DocumentCache(None if args.no_cache else args.cache_dir)
    client = YargitayClient(UrlLibTransport(config), cache, config.base_url)
    if args.command == "health":
        return client.health()
    if args.command == "search":
        return client.search(
            _criteria_from_args(args), page=args.page, page_size=args.page_size
        )
    if args.command == "search-all":
        return client.search_all(
            _criteria_from_args(args),
            page_size=args.page_size,
            max_results=args.max_results,
            max_pages=args.max_pages,
        )
    if args.command == "get":
        return client.get_document(args.document_id, refresh=args.refresh)
    raise AssertionError(f"unknown command: {args.command}")


def main(argv: Sequence[str] | None = None) -> int:
    _configure_stdio()
    try:
        args = build_parser().parse_args(argv)
        result = run(args)
        json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        return 0
    except YargitayError as exc:
        json.dump({"ok": False, "error": exc.as_dict()}, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        return 2
    except KeyboardInterrupt:
        json.dump(
            {
                "ok": False,
                "error": {
                    "code": "interrupted",
                    "message": "Interrupted by user.",
                    "retryable": True,
                },
            },
            sys.stdout,
            ensure_ascii=False,
            indent=2,
        )
        sys.stdout.write("\n")
        return 130


def _configure_stdio() -> None:
    """Keep JSON and diagnostics UTF-8 on Windows and redirected consoles."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="strict")


if __name__ == "__main__":
    raise SystemExit(main())

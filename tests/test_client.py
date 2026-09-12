from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "yargitay-research" / "scripts" / "yargitay.py"
SPEC = importlib.util.spec_from_file_location("yargitay", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
yargitay = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = yargitay
SPEC.loader.exec_module(yargitay)


def search_response(*rows: Mapping[str, Any], total: int | None = None) -> dict[str, Any]:
    return {
        "data": {
            "data": list(rows),
            "recordsTotal": len(rows) if total is None else total,
            "recordsFiltered": len(rows) if total is None else total,
        },
        "metadata": {},
    }


class FakeTransport:
    def __init__(self, responses: list[Mapping[str, Any]]) -> None:
        self.responses = list(responses)
        self.calls: list[dict[str, Any]] = []

    def request_json(
        self,
        method: str,
        path: str,
        *,
        payload: Mapping[str, Any] | None = None,
        params: Mapping[str, str] | None = None,
    ) -> Mapping[str, Any]:
        self.calls.append(
            {"method": method, "path": path, "payload": payload, "params": params}
        )
        if not self.responses:
            raise AssertionError("unexpected request")
        return self.responses.pop(0)


class FakeHttpResponse:
    def __init__(
        self,
        body: bytes,
        *,
        status: int = 200,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        self.body = body
        self.status = status
        self.headers = dict(headers or {"Content-Type": "application/json"})

    def __enter__(self) -> "FakeHttpResponse":
        return self

    def __exit__(self, *args: Any) -> None:
        return None

    def read(self, amount: int | None = None) -> bytes:
        return self.body if amount is None else self.body[:amount]


class FakeOpener:
    def __init__(self, responses: list[Any]) -> None:
        self.responses = list(responses)
        self.calls = 0

    def open(self, request: Any, timeout: float) -> Any:
        self.calls += 1
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class FakeClock:
    def __init__(self, value: float = 100.0) -> None:
        self.value = value
        self.sleeps: list[float] = []

    def __call__(self) -> float:
        return self.value

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.value += seconds


class SearchTests(unittest.TestCase):
    def test_search_builds_official_payload_and_normalizes_result(self) -> None:
        transport = FakeTransport(
            [
                search_response(
                    {
                        "id": 123,
                        "daire": "Ceza Genel Kurulu",
                        "esasNo": "2023/12",
                        "kararNo": "2024/34",
                        "kararTarihi": "14.03.2024",
                    },
                    total=42,
                )
            ]
        )
        client = yargitay.YargitayClient(transport)
        criteria = yargitay.SearchCriteria(
            query='"TCK 32"', chamber="Ceza Genel Kurulu", date_from="01.01.2024"
        )

        result = client.search(criteria, page=2, page_size=20)

        data = transport.calls[0]["payload"]["data"]
        self.assertEqual(data["aranan"], '"TCK 32"')
        self.assertEqual(data["arananKelime"], '"TCK 32"')
        self.assertEqual(data["birimYrgKurulDaire"], "Ceza Genel Kurulu")
        self.assertEqual(data["pageNumber"], 2)
        self.assertEqual(result["total"], 42)
        self.assertTrue(result["has_more"])
        self.assertEqual(result["results"][0]["id"], "123")
        self.assertEqual(result["results"][0]["karar_tarihi_iso"], "2024-03-14")
        self.assertEqual(
            result["results"][0]["official_source_url"],
            "https://karararama.yargitay.gov.tr/getDokuman?id=123",
        )

    def test_search_omits_empty_optional_filters(self) -> None:
        transport = FakeTransport([search_response()])
        client = yargitay.YargitayClient(transport)

        client.search(yargitay.SearchCriteria(query="vesayet"), page=1, page_size=10)

        data = transport.calls[0]["payload"]["data"]
        self.assertNotIn("birimYrgKurulDaire", data)
        self.assertNotIn("baslangicTarihi", data)

    def test_all_chamber_is_omitted(self) -> None:
        transport = FakeTransport([search_response()])
        client = yargitay.YargitayClient(transport)

        client.search(
            yargitay.SearchCriteria(query="vesayet", chamber="ALL"),
            page=1,
            page_size=10,
        )

        data = transport.calls[0]["payload"]["data"]
        self.assertNotIn("birimYrgKurulDaire", data)

    def test_schema_change_fails_closed(self) -> None:
        client = yargitay.YargitayClient(FakeTransport([{"data": {"items": []}}]))

        with self.assertRaises(yargitay.YargitayError) as context:
            client.search(yargitay.SearchCriteria(query="test"), page=1, page_size=10)

        self.assertEqual(context.exception.code, "schema_changed")

    def test_invalid_inputs_are_rejected_before_network(self) -> None:
        transport = FakeTransport([])
        client = yargitay.YargitayClient(transport)

        with self.assertRaises(yargitay.YargitayError):
            client.search(yargitay.SearchCriteria(), page=1, page_size=10)
        with self.assertRaises(yargitay.YargitayError):
            client.search(
                yargitay.SearchCriteria(query="test", date_from="2024-01-01"),
                page=1,
                page_size=10,
            )
        with self.assertRaises(yargitay.YargitayError):
            client.search(yargitay.SearchCriteria(query="test"), page=0, page_size=10)
        with self.assertRaises(yargitay.YargitayError):
            client.search(
                yargitay.SearchCriteria(case_year="2024", case_first="1"),
                page=1,
                page_size=10,
            )
        self.assertEqual(transport.calls, [])

    def test_search_all_deduplicates_and_stops_at_bound(self) -> None:
        row1 = {"id": "1", "daire": "1. Hukuk Dairesi"}
        row2 = {"id": "2", "daire": "1. Hukuk Dairesi"}
        row3 = {"id": "3", "daire": "1. Hukuk Dairesi"}
        transport = FakeTransport(
            [
                search_response(row1, row2, total=4),
                search_response(row2, row3, total=4),
            ]
        )
        client = yargitay.YargitayClient(transport)

        result = client.search_all(
            yargitay.SearchCriteria(query="tapu"),
            page_size=2,
            max_results=3,
            max_pages=4,
        )

        self.assertEqual([item["id"] for item in result["results"]], ["1", "2", "3"])
        self.assertEqual(result["pages_fetched"], 2)
        self.assertEqual(result["returned"], 3)
        self.assertTrue(result["truncated"])

    def test_search_all_obeys_page_limit(self) -> None:
        row = {"id": "1", "daire": "1. Hukuk Dairesi"}
        transport = FakeTransport(
            [search_response(row, total=100), search_response(row, total=100)]
        )
        client = yargitay.YargitayClient(transport)

        result = client.search_all(
            yargitay.SearchCriteria(query="tapu"),
            page_size=1,
            max_results=10,
            max_pages=2,
        )

        self.assertEqual(len(transport.calls), 2)
        self.assertEqual(result["stop_reason"], "page_limit")
        self.assertEqual(result["pages_fetched"], 2)


class DocumentTests(unittest.TestCase):
    def test_html_parser_preserves_structure_and_drops_active_content(self) -> None:
        parser = yargitay.DecisionHtmlParser()
        parser.feed(
            "<html><style>hidden</style><body><b>Başlık</b><br>Birinci satır"
            "<p>İkinci&nbsp;satır</p><script>ignore()</script></body></html>"
        )

        self.assertEqual(parser.text(), "Başlık\nBirinci satır\nİkinci satır")

    def test_get_document_returns_official_text_and_uses_cache(self) -> None:
        transport = FakeTransport([{"data": "<p>Karar metni</p>", "metadata": {}}])
        with tempfile.TemporaryDirectory() as temporary:
            cache = yargitay.DocumentCache(Path(temporary))
            client = yargitay.YargitayClient(transport, cache)

            first = client.get_document("123")
            second = client.get_document("123")

        self.assertEqual(first["text"], "Karar metni")
        self.assertEqual(first["cache"], "miss")
        self.assertEqual(second["cache"], "hit")
        self.assertTrue(second["official_source_retrieved"])
        self.assertEqual(len(transport.calls), 1)

    def test_empty_document_fails_verification(self) -> None:
        client = yargitay.YargitayClient(FakeTransport([{"data": "<html></html>"}]))

        with self.assertRaises(yargitay.YargitayError) as context:
            client.get_document("123")

        self.assertEqual(context.exception.code, "document_not_found")

    def test_cache_ignores_corrupt_and_old_entries(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            cache = yargitay.DocumentCache(directory)
            (directory / "1.json").write_text("not json", encoding="utf-8")
            (directory / "2.json").write_text(
                json.dumps({"cache_version": 0}), encoding="utf-8"
            )

            self.assertIsNone(cache.get("1"))
            self.assertIsNone(cache.get("2"))


class ErrorContractTests(unittest.TestCase):
    def test_error_contract_is_stable(self) -> None:
        error = yargitay.YargitayError(
            "rate_limited", "wait", retryable=True, details={"status": 429}
        )
        self.assertEqual(
            error.as_dict(),
            {
                "code": "rate_limited",
                "message": "wait",
                "retryable": True,
                "details": {"status": 429},
            },
        )

    def test_turkish_json_is_emitted_without_ascii_escaping(self) -> None:
        value = {"text": "İçtihat, hüküm ve değerlendirme"}
        encoded = json.dumps(value, ensure_ascii=False).encode("utf-8")

        self.assertIn("İçtihat".encode("utf-8"), encoded)
        self.assertNotIn(b"\\u0130", encoded)

    def test_invalid_cli_arguments_return_json(self) -> None:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            exit_code = yargitay.main(["search", "--unknown-option"])

        value = json.loads(output.getvalue())
        self.assertEqual(exit_code, 2)
        self.assertFalse(value["ok"])
        self.assertEqual(value["error"]["code"], "invalid_arguments")


class TransportTests(unittest.TestCase):
    def test_429_uses_retry_after_then_succeeds(self) -> None:
        rate_limit = urllib.error.HTTPError(
            "https://example.test/search",
            429,
            "Too Many Requests",
            {"Retry-After": "7"},
            io.BytesIO(b"limited"),
        )
        opener = FakeOpener(
            [
                FakeHttpResponse(b"index", headers={"Content-Type": "text/html"}),
                rate_limit,
                FakeHttpResponse(b'{"data":{"data":[],"recordsTotal":0}}'),
            ]
        )
        sleeps: list[float] = []
        transport = yargitay.UrlLibTransport(
            yargitay.ClientConfig(
                base_url="https://example.test",
                min_interval=0,
                max_retries=1,
            ),
            sleep=sleeps.append,
            opener=opener,
        )

        result = transport.request_json("POST", "/search", payload={"data": {}})

        self.assertEqual(result["data"]["recordsTotal"], 0)
        self.assertEqual(sleeps, [7.0])
        self.assertEqual(opener.calls, 3)

    def test_non_json_response_is_rejected(self) -> None:
        opener = FakeOpener(
            [
                FakeHttpResponse(b"index", headers={"Content-Type": "text/html"}),
                FakeHttpResponse(b"not-json", headers={"Content-Type": "text/html"}),
            ]
        )
        transport = yargitay.UrlLibTransport(
            yargitay.ClientConfig(base_url="https://example.test", min_interval=0),
            opener=opener,
        )

        with self.assertRaises(yargitay.YargitayError) as context:
            transport.request_json("GET", "/document")

        self.assertEqual(context.exception.code, "invalid_response")

    def test_json_rate_limit_envelope_is_retried(self) -> None:
        error_body = json.dumps(
            {
                "data": None,
                "metadata": {
                    "FMTY": "ERROR",
                    "FMC": "RATE_LIMIT",
                    "FMTE": "Çok fazla istek gönderildi.",
                },
            },
            ensure_ascii=False,
        ).encode("utf-8")
        opener = FakeOpener(
            [
                FakeHttpResponse(b"index", headers={"Content-Type": "text/html"}),
                FakeHttpResponse(error_body),
                FakeHttpResponse(b'{"data":{"data":[],"recordsTotal":0}}'),
            ]
        )
        sleeps: list[float] = []
        transport = yargitay.UrlLibTransport(
            yargitay.ClientConfig(
                base_url="https://example.test",
                min_interval=0,
                max_retries=1,
                retry_base=0,
            ),
            sleep=sleeps.append,
            opener=opener,
        )

        result = transport.request_json("POST", "/search", payload={"data": {}})

        self.assertEqual(result["data"]["recordsTotal"], 0)
        self.assertEqual(opener.calls, 3)
        self.assertEqual(sleeps, [0.0])

    def test_unknown_json_error_envelope_is_temporary_upstream_error(self) -> None:
        error_body = json.dumps(
            {
                "data": None,
                "metadata": {
                    "FMTY": "ERROR",
                    "FMC": "ADALET_EMPTY_EXCEPTION",
                    "FMTE": "Temporary backend failure",
                },
            }
        ).encode("utf-8")
        opener = FakeOpener(
            [
                FakeHttpResponse(b"index", headers={"Content-Type": "text/html"}),
                FakeHttpResponse(error_body),
            ]
        )
        transport = yargitay.UrlLibTransport(
            yargitay.ClientConfig(
                base_url="https://example.test",
                min_interval=0,
                max_retries=0,
            ),
            opener=opener,
        )

        with self.assertRaises(yargitay.YargitayError) as context:
            transport.request_json("GET", "/document")

        self.assertEqual(context.exception.code, "upstream_error")
        self.assertTrue(context.exception.retryable)
        self.assertEqual(
            context.exception.details["official_code"], "ADALET_EMPTY_EXCEPTION"
        )

    def test_invalid_request_envelope_is_not_retried(self) -> None:
        error_body = json.dumps(
            {
                "data": None,
                "metadata": {
                    "FMTY": "ERROR",
                    "FMC": "ADALET_EMPTY_EXCEPTION",
                    "FMTE": 'Cannot deserialize value "4-1386": not a valid Integer',
                },
            }
        ).encode("utf-8")
        opener = FakeOpener(
            [
                FakeHttpResponse(b"index", headers={"Content-Type": "text/html"}),
                FakeHttpResponse(error_body),
            ]
        )
        transport = yargitay.UrlLibTransport(
            yargitay.ClientConfig(
                base_url="https://example.test",
                min_interval=0,
                max_retries=2,
            ),
            opener=opener,
        )

        with self.assertRaises(yargitay.YargitayError) as context:
            transport.request_json("POST", "/search", payload={"data": {}})

        self.assertEqual(context.exception.code, "official_error")
        self.assertFalse(context.exception.retryable)
        self.assertEqual(opener.calls, 2)

    def test_shared_rate_limiter_spaces_separate_instances(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            state_path = Path(temporary) / "request-rate-limit"
            clock = FakeClock()
            first = yargitay.SharedRateLimiter(
                state_path,
                3.0,
                sleep=clock.sleep,
                clock=clock,
                monotonic=clock,
            )
            second = yargitay.SharedRateLimiter(
                state_path,
                3.0,
                sleep=clock.sleep,
                clock=clock,
                monotonic=clock,
            )

            self.assertTrue(first.wait())
            self.assertTrue(second.wait())

            self.assertEqual(clock.sleeps, [3.0])
            self.assertEqual(float(state_path.read_text(encoding="ascii")), 103.0)


if __name__ == "__main__":
    unittest.main()

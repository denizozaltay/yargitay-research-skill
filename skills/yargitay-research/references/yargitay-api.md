# Yargıtay web endpoint reference

This is a debugging reference for the public website used by
`scripts/yargitay.py`. It is not official developer API documentation.

Last live verification: **12 September 2026**.

## Status and stability

Base URL: `https://karararama.yargitay.gov.tr`

The website frontend currently uses internal JSON endpoints. They may change
without notice. A `schema_changed` error should be investigated against the
current frontend before modifying the client. Do not silently fall back to a
secondary legal database for verification.

The service sets session cookies when `/index` is loaded. Direct calls may work
without them, but the client bootstraps a cookie-aware session first.

## Search

```http
POST /aramadetaylist
Content-Type: application/json; charset=UTF-8
Accept: application/json, text/plain, */*
X-Requested-With: XMLHttpRequest
```

Minimal body:

```json
{
  "data": {
    "aranan": "TCK 32",
    "arananKelime": "TCK 32",
    "pageSize": 20,
    "pageNumber": 1
  }
}
```

Both `aranan` and `arananKelime` are sent because the current frontend contract
expects them. Optional non-empty fields are:

| API field | Meaning |
|---|---|
| `birimYrgKurulDaire` | Exact chamber/board display name |
| `esasYil` | Esas year |
| `esasIlkSiraNo`, `esasSonSiraNo` | Esas number range |
| `kararYil` | Karar year |
| `kararIlkSiraNo`, `kararSonSiraNo` | Karar number range |
| `baslangicTarihi`, `bitisTarihi` | Decision dates in `DD.MM.YYYY` |

Omit unused filters. In particular, do not send `"ALL"` as the chamber; omit
the chamber field to search all units. The observed page-size range is 1–100.

Expected response shape:

```json
{
  "data": {
    "data": [
      {
        "id": "1224730600",
        "daire": "10. Hukuk Dairesi",
        "esasNo": "2026/13493",
        "kararNo": "2026/10056",
        "kararTarihi": "01.07.2026",
        "arananKelime": "TCK 32",
        "index": 1,
        "siraNo": 1
      }
    ],
    "recordsTotal": 1,
    "recordsFiltered": 1
  },
  "metadata": {}
}
```

The numbers above illustrate the schema; do not use them as legal authority.

## Full document

```http
GET /getDokuman?id=DOCUMENT_ID
Accept: application/json, text/plain, */*
```

Expected response:

```json
{
  "data": "<html>...official decision full text...</html>",
  "metadata": {}
}
```

The client removes executable/style elements and converts the HTML to readable
text. The official source URL retained in output is the same endpoint URL.

## Rate limiting and errors

Rapid requests can produce HTTP 429 or an HTML access-limit page. The client
spaces requests by three seconds by default and performs bounded exponential
backoff. The spacing timestamp is shared through the cache directory so separate
CLI processes do not reset the limiter. `--no-cache` disables document caching,
not this access protection. Preserve the default interval for ordinary research;
do not evade access controls or run aggressive parallel requests.

The website can also return HTTP 200 with a JSON error envelope instead of the
normal payload:

```json
{
  "data": null,
  "metadata": {
    "FMTY": "ERROR",
    "FMC": "...",
    "FMTE": "..."
  }
}
```

The client examines this envelope before validating the success schema. Known
access-limit messages become retryable `rate_limited` errors; unknown server
error envelopes become retryable `upstream_error` errors; invalid request data
becomes non-retryable `official_error`. A response is classified as
`schema_changed` only when it is not an official error envelope and its success
shape no longer matches the expected contract.

Likely failure categories:

- `network_error`: connection, TLS, DNS, or timeout failure;
- `rate_limited`: HTTP 429 or an access-limit page;
- `upstream_error`: retryable HTTP 5xx;
- `official_error`: the website rejected invalid request data;
- `invalid_response`: expected JSON was not returned;
- `schema_changed`: JSON no longer matches the known contract;
- `document_not_found`: no usable full text was returned.

## Raw curl diagnostics

Use only for debugging the canonical Python client. Load `/index` first if the
endpoint appears to require a session. A minimal search request is:

```bash
curl 'https://karararama.yargitay.gov.tr/aramadetaylist' \
  -H 'Accept: application/json, text/plain, */*' \
  -H 'Content-Type: application/json; charset=UTF-8' \
  -H 'X-Requested-With: XMLHttpRequest' \
  -H 'Origin: https://karararama.yargitay.gov.tr' \
  -H 'Referer: https://karararama.yargitay.gov.tr/index' \
  --data-raw '{"data":{"aranan":"TCK 32","arananKelime":"TCK 32","pageSize":10,"pageNumber":1}}'
```

Document retrieval:

```bash
curl 'https://karararama.yargitay.gov.tr/getDokuman?id=DOCUMENT_ID' \
  -H 'Accept: application/json, text/plain, */*' \
  -H 'Referer: https://karararama.yargitay.gov.tr/index'
```

When debugging a suspected schema change, compare the current `/index`
JavaScript request construction, HTTP status and content type, JSON envelope,
and field types. Update this reference and fixtures together with any code fix.

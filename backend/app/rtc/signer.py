"""Volcengine OpenAPI request signing (HMAC-SHA256 V4) for the rtc service."""

from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timezone
from urllib.parse import quote


def sign_rtc_openapi_request(
    *,
    access_key: str,
    secret_key: str,
    method: str,
    host: str,
    path: str,
    query: dict[str, str],
    body: str,
    region: str = "cn-north-1",
    service: str = "rtc",
    now: datetime | None = None,
) -> dict[str, str]:
    moment = now or datetime.now(timezone.utc)
    x_date = moment.strftime("%Y%m%dT%H%M%SZ")
    short_date = moment.strftime("%Y%m%d")

    payload_hash = hashlib.sha256(body.encode("utf-8")).hexdigest()
    headers = {
        "Host": host,
        "Content-Type": "application/json",
        "X-Date": x_date,
        "X-Content-Sha256": payload_hash,
    }

    signed_header_names = sorted(name.lower() for name in headers)
    signed_headers = ";".join(signed_header_names)
    canonical_headers = "".join(f"{name.lower()}:{headers[name]}\n" for name in sorted(headers))

    canonical_query = "&".join(
        f"{quote(key, safe='')}={quote(value, safe='')}" for key, value in sorted(query.items())
    )
    canonical_request = "\n".join(
        [
            method.upper(),
            path,
            canonical_query,
            canonical_headers,
            signed_headers,
            payload_hash,
        ]
    )

    credential_scope = f"{short_date}/{region}/{service}/request"
    string_to_sign = "\n".join(
        [
            "HMAC-SHA256",
            x_date,
            credential_scope,
            hashlib.sha256(canonical_request.encode("utf-8")).hexdigest(),
        ]
    )

    signing_key = _derive_signing_key(secret_key, short_date, region, service)
    signature = hmac.new(signing_key, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()
    authorization = (
        f"HMAC-SHA256 Credential={access_key}/{credential_scope}, "
        f"SignedHeaders={signed_headers}, Signature={signature}"
    )

    return {
        **headers,
        "Authorization": authorization,
    }


def _derive_signing_key(secret_key: str, short_date: str, region: str, service: str) -> bytes:
    key = secret_key.encode("utf-8")
    k_date = hmac.new(key, short_date.encode("utf-8"), hashlib.sha256).digest()
    k_region = hmac.new(k_date, region.encode("utf-8"), hashlib.sha256).digest()
    k_service = hmac.new(k_region, service.encode("utf-8"), hashlib.sha256).digest()
    return hmac.new(k_service, b"request", hashlib.sha256).digest()

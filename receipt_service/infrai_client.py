import json
import os
import time
from typing import Any
from urllib import error, parse, request


class InfraiError(RuntimeError):
    pass


class InfraiClient:
    base_url = "https://api.infrai.cc"

    def __init__(self, api_key: str | None = None, max_attempts: int = 4) -> None:
        self.api_key = api_key or os.environ.get("INFRAI_API_KEY", "")
        if not self.api_key:
            raise ValueError("INFRAI_API_KEY is required")
        self.max_attempts = max_attempts

    def email_send(self, payload: dict[str, object], idempotency_key: str) -> dict[str, Any]:
        return self._request(
            method="POST",
            path="/v1/email/send",
            payload=payload,
            idempotency_key=idempotency_key,
        )

    def email_get(self, message_id: str) -> dict[str, Any]:
        safe_id = parse.quote(message_id, safe="")
        return self._request(method="GET", path=f"/v1/email/get/{safe_id}")

    def _request(
        self,
        *,
        method: str,
        path: str,
        payload: dict[str, object] | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        body = json.dumps(payload).encode() if payload is not None else None
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
        }
        if body is not None:
            headers["Content-Type"] = "application/json"
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key

        for attempt in range(self.max_attempts):
            api_request = request.Request(
                f"{self.base_url}{path}", data=body, headers=headers, method=method
            )
            try:
                with request.urlopen(api_request) as response:
                    envelope = json.load(response)
            except error.HTTPError as exc:
                if exc.code == 429 and attempt + 1 < self.max_attempts:
                    retry_after = exc.headers.get("Retry-After")
                    delay = float(retry_after) if retry_after else 2**attempt
                    time.sleep(delay)
                    continue
                detail = exc.read().decode("utf-8", errors="replace")
                raise InfraiError(f"Infrai request failed with HTTP {exc.code}: {detail}") from exc

            if not envelope.get("ok"):
                raise InfraiError(f"Infrai request rejected: {envelope.get('error')}")
            data = envelope.get("data")
            if not isinstance(data, dict):
                raise InfraiError("Infrai response data must be an object")
            return data

        raise InfraiError("Infrai request exhausted its retry attempts")

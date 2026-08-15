import json
from typing import Any

import httpx
from pydantic import ValidationError

from app.domain.scripts.models import ScriptDraft
from app.ports.script_provider import (
    ProviderOutputInvalid,
    ProviderRateLimited,
    ProviderUnavailable,
    ScriptGenerationRequest,
)


def _strict_json_schema(value: object) -> object:
    if isinstance(value, dict):
        strict = {key: _strict_json_schema(item) for key, item in value.items()}
        properties = strict.get("properties")
        if isinstance(properties, dict):
            strict["additionalProperties"] = False
            strict["required"] = list(properties)
        return strict
    if isinstance(value, list):
        return [_strict_json_schema(item) for item in value]
    return value


class OpenAICompatibleScriptProvider:
    def __init__(
        self,
        *,
        client: httpx.AsyncClient,
        base_url: str,
        model: str,
        api_key: str,
    ) -> None:
        self.client = client
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.last_attempt_count = 0

    async def generate(self, request: ScriptGenerationRequest) -> ScriptDraft:
        messages: list[dict[str, str]] = [
            {
                "role": "system",
                "content": (
                    "Return only a JSON script matching the supplied schema. "
                    "Use only supplied facts and bind each product claim to fact IDs. "
                    "Never render excluded facts in any visible script field."
                ),
            },
            {"role": "user", "content": self._provider_input(request)},
        ]
        invalid_content = ""
        for attempt in range(2):
            self.last_attempt_count = attempt + 1
            if attempt:
                messages.extend(
                    [
                        {"role": "assistant", "content": invalid_content[:8000]},
                        {
                            "role": "user",
                            "content": "Repair the format. Return only valid JSON matching the schema.",
                        },
                    ]
                )
            try:
                invalid_content = await self._request_completion(messages)
            except (ProviderRateLimited, ProviderUnavailable, ProviderOutputInvalid) as exc:
                exc.attempt_count = self.last_attempt_count
                raise
            try:
                return ScriptDraft.model_validate_json(invalid_content)
            except (ValidationError, ValueError, json.JSONDecodeError):
                continue
        raise ProviderOutputInvalid(
            "Provider output did not match ScriptDraft",
            attempt_count=self.last_attempt_count,
        )

    @staticmethod
    def _provider_input(request: ScriptGenerationRequest) -> str:
        payload = request.model_dump(mode="json")
        payload.pop("audience", None)
        payload.pop("promotion", None)
        pattern = payload.get("pattern_definition")
        if isinstance(pattern, dict):
            pattern.pop("audience_policy", None)
            pattern.pop("server_owned_copy", None)
            pattern.pop("cta_policy", None)
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

    async def _request_completion(self, messages: list[dict[str, str]]) -> str:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "script_draft",
                    "strict": True,
                    "schema": _strict_json_schema(ScriptDraft.model_json_schema()),
                },
            },
        }
        try:
            response = await self.client.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=payload,
                timeout=httpx.Timeout(30, connect=5),
            )
        except httpx.TimeoutException as exc:
            raise ProviderUnavailable("Provider request timed out") from exc
        except httpx.RequestError as exc:
            raise ProviderUnavailable("Provider request failed") from exc

        if response.status_code == 429:
            raise ProviderRateLimited("Provider rate limit reached")
        try:
            response.raise_for_status()
            body = response.json()
            content = body["choices"][0]["message"]["content"]
        except (httpx.HTTPStatusError, KeyError, IndexError, TypeError, ValueError) as exc:
            raise ProviderUnavailable("Provider returned an unusable response") from exc
        if not isinstance(content, str):
            raise ProviderOutputInvalid("Provider content must be a JSON string")
        return content

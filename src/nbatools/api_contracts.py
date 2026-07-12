"""Shared request validation for every public query HTTP transport."""

from __future__ import annotations

import inspect
from functools import cache
from typing import Any, get_type_hints

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    TypeAdapter,
    ValidationError,
    ValidationInfo,
    field_validator,
)

NATURAL_QUERY_MAX_LENGTH = 500
STRUCTURED_ROUTE_MAX_LENGTH = 64

_NON_HTTP_ROUTE_KWARGS = frozenset({"df", "player_df"})
_ORCHESTRATION_KWARG_TYPES: dict[str, Any] = {
    "opponent_quality": dict[str, Any],
    "opponent_conference": str,
    "opponent_division": str,
    "clutch": bool,
    "quarter": str,
    "half": str,
    "role": str,
    "back_to_back": bool,
    "rest_days": str | int,
    "one_possession": bool,
    "nationally_televised": bool,
}


class NaturalQueryRequest(BaseModel):
    """Strict natural-query request shared by FastAPI and Vercel."""

    model_config = ConfigDict(extra="forbid", strict=True)

    query: str = Field(
        ...,
        min_length=1,
        max_length=NATURAL_QUERY_MAX_LENGTH,
        description="Natural-language NBA query text.",
    )

    @field_validator("query")
    @classmethod
    def _query_must_contain_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must contain non-whitespace text")
        return value


class StructuredQueryRequest(BaseModel):
    """Strict route request shared by FastAPI and Vercel."""

    model_config = ConfigDict(extra="forbid", strict=True)

    route: str = Field(
        ...,
        min_length=1,
        max_length=STRUCTURED_ROUTE_MAX_LENGTH,
        description="Named route (e.g. 'player_game_summary').",
    )
    kwargs: dict[str, Any] = Field(
        default_factory=dict,
        description="Keyword arguments forwarded to the route's build_result function.",
    )

    @field_validator("route")
    @classmethod
    def _route_must_contain_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must contain non-whitespace text")
        return value

    @field_validator("kwargs")
    @classmethod
    def _kwargs_must_match_route(
        cls,
        value: dict[str, Any],
        info: ValidationInfo,
    ) -> dict[str, Any]:
        route = info.data.get("route")
        if isinstance(route, str):
            validate_structured_route_kwargs(route, value)
        return value


@cache
def _structured_route_contract(
    route: str,
) -> tuple[frozenset[str], dict[str, TypeAdapter[Any]]] | None:
    from nbatools.commands._natural_query_execution import _get_build_result_map

    build_function = _get_build_result_map().get(route)
    if build_function is None:
        return None

    signature = inspect.signature(build_function)
    type_hints = get_type_hints(build_function)
    required: set[str] = set()
    adapters: dict[str, TypeAdapter[Any]] = {}

    for name, parameter in signature.parameters.items():
        if (
            parameter.kind
            in {
                inspect.Parameter.VAR_POSITIONAL,
                inspect.Parameter.VAR_KEYWORD,
            }
            or name in _NON_HTTP_ROUTE_KWARGS
        ):
            continue
        if parameter.default is inspect.Parameter.empty:
            required.add(name)
        annotation = type_hints.get(name, Any)
        adapters[name] = TypeAdapter(annotation)

    for name, annotation in _ORCHESTRATION_KWARG_TYPES.items():
        adapters.setdefault(name, TypeAdapter(annotation))

    return frozenset(required), adapters


def validate_structured_route_kwargs(route: str, kwargs: dict[str, Any]) -> None:
    """Reject unsafe structured kwargs before they reach route execution."""
    contract = _structured_route_contract(route)
    if contract is None:
        return

    required, adapters = contract
    unknown = sorted(set(kwargs) - set(adapters))
    if unknown:
        fields = ", ".join(unknown)
        raise ValueError(f"unsupported field(s) for route '{route}': {fields}")

    missing = sorted(required - set(kwargs))
    if missing:
        fields = ", ".join(missing)
        raise ValueError(f"missing required field(s) for route '{route}': {fields}")

    for name, value in kwargs.items():
        try:
            adapters[name].validate_python(value, strict=True)
        except ValidationError as exc:
            raise ValueError(f"field '{name}' has the wrong type for route '{route}'") from exc


def validation_error_payload(error: Any) -> dict[str, Any]:
    """Return one stable public validation envelope for Pydantic/FastAPI errors."""
    errors = error.errors()
    if errors:
        first = errors[0]
        location = ".".join(
            str(part) for part in first.get("loc", ()) if str(part) not in {"body", "__root__"}
        )
        if not location and first.get("type") in {"model_attributes_type", "model_type"}:
            detail = "Request body must be a JSON object"
        else:
            message = str(first.get("msg") or "Invalid request")
            if message.startswith("Value error, "):
                message = message.removeprefix("Value error, ")
            detail = f"{location}: {message}" if location else message
    else:
        detail = "Invalid request"
    return {"ok": False, "error": "validation_error", "detail": detail}

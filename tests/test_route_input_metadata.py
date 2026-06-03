from __future__ import annotations

import importlib
import inspect

from nbatools.query_service import VALID_ROUTES
from nbatools.route_input_metadata import ROUTE_INPUT_METADATA, RouteInputMetadata


def _one_of_kwargs(metadata: RouteInputMetadata) -> set[str]:
    names: set[str] = set()
    for group in metadata.one_of_groups:
        for option in group.options:
            names.update(option)
    return names


def _implementation_callable(metadata: RouteInputMetadata):
    module = importlib.import_module(metadata.implementation_module)
    return getattr(module, metadata.implementation_function)


def _signature_kwargs(metadata: RouteInputMetadata) -> tuple[set[str], set[str] | None]:
    signature = inspect.signature(_implementation_callable(metadata))
    accepted: set[str] = set()
    required: set[str] = set()

    for name, param in signature.parameters.items():
        if param.kind == inspect.Parameter.VAR_KEYWORD:
            return accepted, None
        if param.kind not in (
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            inspect.Parameter.KEYWORD_ONLY,
        ):
            continue
        accepted.add(name)
        if param.default is inspect.Parameter.empty:
            required.add(name)

    return accepted, required


def test_route_input_metadata_covers_every_valid_route():
    assert set(ROUTE_INPUT_METADATA) == set(VALID_ROUTES)


def test_route_input_metadata_required_fields_are_present():
    for route, metadata in ROUTE_INPUT_METADATA.items():
        assert metadata.route == route
        assert metadata.implementation_module
        assert metadata.implementation_function
        assert metadata.description


def test_route_input_metadata_has_examples_or_explicit_notes():
    for metadata in ROUTE_INPUT_METADATA.values():
        assert metadata.examples or metadata.notes


def test_route_input_metadata_signature_alignment_is_practical():
    for metadata in ROUTE_INPUT_METADATA.values():
        accepted, required = _signature_kwargs(metadata)
        if required is None:
            continue

        documented = metadata.documented_kwargs
        dispatch_only = set(metadata.dispatch_only_kwargs)
        unknown = documented - accepted - dispatch_only
        assert not unknown, f"{metadata.route} documents unknown kwargs: {sorted(unknown)}"

        documented_required = set(metadata.required_kwargs) | _one_of_kwargs(metadata)
        missing_required = required - documented_required
        assert not missing_required, (
            f"{metadata.route} does not document signature-required kwargs: "
            f"{sorted(missing_required)}"
        )

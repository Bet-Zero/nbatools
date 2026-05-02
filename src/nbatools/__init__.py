__all__ = ["__version__", "execute_natural_query", "execute_structured_query", "QueryResult"]
__version__ = "0.7.0"


def __getattr__(name: str):
    """Lazily expose query-service convenience imports."""
    if name in {"QueryResult", "execute_natural_query", "execute_structured_query"}:
        from nbatools import query_service

        value = getattr(query_service, name)
        globals()[name] = value
        return value
    raise AttributeError(f"module 'nbatools' has no attribute {name!r}")

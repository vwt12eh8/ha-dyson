"""Utilities for Dyson Local."""

from typing import overload

from .libdyson.const import Environmental


def is_available(value: int | float | Environmental | None):
    return value not in (Environmental.OFF, Environmental.FAIL)


@overload
def filter_unavailable(value: int | Environmental | None) -> int | None:
    ...


@overload
def filter_unavailable(value: float | Environmental | None) -> float | None:
    ...


def filter_unavailable(value: int | float | Environmental | None):
    if not is_available(value):
        return None
    if isinstance(value, Environmental):
        return None
    return value

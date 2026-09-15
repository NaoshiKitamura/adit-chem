"""Common base class for the exceptions ADIT raises, so callers can separate them from other failures."""

from __future__ import annotations


class AditError(Exception):
    """Base class for failures that carry a message meant for the user."""


class AditValueError(AditError, ValueError):
    pass

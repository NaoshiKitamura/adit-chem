
try:  # pragma: no
    from importlib.metadata import version as _version

    __version__ = _version("adit-chem")
except Exception:  # pragma: no cover
    __version__ = "0.1.0a1"

LOCAL_FRONTEND_ORIGINS = ("http://localhost:3000", "http://127.0.0.1:3000")


def build_cors_origins(configured_origins: str | None, frontend_url: str) -> list[str]:
    """Return explicit browser origins for local and deployed environments."""
    origins = [
        origin.strip().rstrip("/")
        for origin in (configured_origins or "").split(",")
        if origin.strip()
    ]
    for origin in (*LOCAL_FRONTEND_ORIGINS, frontend_url.rstrip("/")):
        if origin and origin not in origins:
            origins.append(origin)
    if "*" in origins:
        raise ValueError("CORS origins must be explicit when credentials are enabled")
    return origins

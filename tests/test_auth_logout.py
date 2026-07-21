import asyncio

from fastapi import FastAPI

from app.api.v1.auth import router


def test_logout_route_is_registered():
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")

    routes = {
        (route.path, method)
        for route in app.routes
        for method in getattr(route, "methods", set())
    }

    assert ("/api/v1/auth/logout", "POST") in routes


def test_logout_confirms_authenticated_session():
    from app.api.v1.auth import logout

    assert asyncio.run(logout(current_user=object())) == {
        "success": True,
        "message": "Logged out",
    }

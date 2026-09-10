"""Authentication middleware for the ATLAS dashboard."""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, RedirectResponse

from atlas.security.auth_service import AuthService


PUBLIC_PATHS = {"/login", "/setup"}


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """Require a valid server-side session for dashboard access."""

    def __init__(self, app, auth_service: AuthService):
        super().__init__(app)
        self.auth_service = auth_service

    async def dispatch(self, request, call_next):
        if request.url.path.startswith("/static/") or request.url.path in PUBLIC_PATHS:
            return await call_next(request)

        user = self.auth_service.get_user_by_session(
            request.cookies.get("atlas_session")
        )
        if user is None:
            if request.url.path.startswith("/api/"):
                return JSONResponse(
                    {"detail": "Authentication required."}, status_code=401
                )
            return RedirectResponse(url="/login", status_code=303)

        request.state.user = user
        return await call_next(request)


def require_role(request, *roles):
    """Return a 403 response unless the authenticated user has an allowed role."""
    user = request.state.user
    if user.role not in roles:
        return JSONResponse({"detail": "Insufficient permissions."}, status_code=403)
    return None

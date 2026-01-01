"""
Authentication Middleware
JWT validation middleware for FastAPI
"""

import time
from typing import Callable, Optional
from uuid import UUID

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from src.auth.jwt_handler import jwt_handler

import logging
logger = logging.getLogger(__name__)


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Authentication middleware that validates JWT tokens
    and adds user info to request state.
    
    This middleware:
    1. Extracts Bearer token from Authorization header
    2. Validates the JWT token
    3. Adds user_id and user_email to request.state
    4. Allows request to continue (actual auth enforcement is in dependencies)
    
    Note: This middleware does NOT block requests - it only enriches them.
    Use FastAPI dependencies (get_current_user) for actual auth enforcement.
    """
    
    # Paths that should skip token extraction entirely
    SKIP_PATHS = [
        "/health",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/api/auth/login",
        "/api/auth/register",
        "/api/auth/refresh",
        "/api/auth/oauth",
    ]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip token extraction for certain paths
        path = request.url.path
        if any(path.startswith(skip) for skip in self.SKIP_PATHS):
            return await call_next(request)
        
        # Extract and validate token
        user_id, user_email = self._extract_user_from_token(request)
        
        # Add user info to request state (available in route handlers)
        request.state.user_id = user_id
        request.state.user_email = user_email
        request.state.is_authenticated = user_id is not None
        
        return await call_next(request)
    
    def _extract_user_from_token(self, request: Request) -> tuple[Optional[UUID], Optional[str]]:
        """
        Extract user info from Authorization header
        
        Returns:
            Tuple of (user_id, user_email) or (None, None) if invalid/missing
        """
        auth_header = request.headers.get("Authorization")
        
        if not auth_header:
            return None, None
        
        # Check Bearer scheme
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return None, None
        
        token = parts[1]
        
        # Verify token
        payload = jwt_handler.verify_token(token, expected_type="access")
        if not payload:
            return None, None
        
        try:
            user_id = UUID(payload.get("sub"))
            user_email = payload.get("email")
            return user_id, user_email
        except (ValueError, TypeError):
            return None, None


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for logging requests and response times
    """
    
    # Paths to exclude from detailed logging
    EXCLUDE_PATHS = ["/health", "/docs", "/redoc", "/openapi.json"]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path
        
        # Skip logging for excluded paths
        if any(path.startswith(exclude) for exclude in self.EXCLUDE_PATHS):
            return await call_next(request)
        
        # Record start time
        start_time = time.time()
        
        # Get user info if available
        user_id = getattr(request.state, "user_id", None)
        
        # Process request
        response = await call_next(request)
        
        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000
        
        # Log request
        log_data = {
            "method": request.method,
            "path": path,
            "status_code": response.status_code,
            "duration_ms": round(duration_ms, 2),
            "user_id": str(user_id) if user_id else None,
        }
        
        if response.status_code >= 400:
            logger.warning(f"Request failed: {log_data}")
        else:
            logger.info(f"Request completed: {log_data}")
        
        # Add timing header
        response.headers["X-Process-Time-Ms"] = str(round(duration_ms, 2))
        
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple in-memory rate limiting middleware
    
    Note: For production, use Redis-based rate limiting
    """
    
    def __init__(
        self,
        app,
        requests_per_minute: int = 60,
        burst_size: int = 10
    ):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.burst_size = burst_size
        self._request_counts: dict[str, list[float]] = {}
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Get client identifier (IP or user_id)
        client_id = self._get_client_id(request)
        
        # Check rate limit
        if not self._is_allowed(client_id):
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded. Please try again later.",
                    "retry_after_seconds": 60
                },
                headers={"Retry-After": "60"}
            )
        
        return await call_next(request)
    
    def _get_client_id(self, request: Request) -> str:
        """Get unique client identifier"""
        # Prefer user_id if authenticated
        user_id = getattr(request.state, "user_id", None)
        if user_id:
            return f"user:{user_id}"
        
        # Fall back to IP address
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return f"ip:{forwarded.split(',')[0].strip()}"
        
        client_host = request.client.host if request.client else "unknown"
        return f"ip:{client_host}"
    
    def _is_allowed(self, client_id: str) -> bool:
        """Check if request is within rate limit"""
        now = time.time()
        window_start = now - 60  # 1 minute window
        
        # Get or initialize request times for this client
        if client_id not in self._request_counts:
            self._request_counts[client_id] = []
        
        # Remove old requests outside window
        self._request_counts[client_id] = [
            t for t in self._request_counts[client_id] if t > window_start
        ]
        
        # Check if within limit
        if len(self._request_counts[client_id]) >= self.requests_per_minute:
            return False
        
        # Record this request
        self._request_counts[client_id].append(now)
        
        # Cleanup old entries periodically (simple garbage collection)
        if len(self._request_counts) > 10000:
            self._cleanup_old_entries(window_start)
        
        return True
    
    def _cleanup_old_entries(self, window_start: float):
        """Remove clients with no recent requests"""
        to_remove = [
            client_id for client_id, times in self._request_counts.items()
            if not times or max(times) < window_start
        ]
        for client_id in to_remove:
            del self._request_counts[client_id]


class CORSAuthMiddleware(BaseHTTPMiddleware):
    """
    CORS middleware with support for Authorization header
    
    Ensures Authorization header is allowed in CORS requests
    """
    
    def __init__(
        self,
        app,
        allow_origins: list[str] = None,
        allow_credentials: bool = True,
        max_age: int = 600
    ):
        super().__init__(app)
        self.allow_origins = allow_origins or ["*"]
        self.allow_credentials = allow_credentials
        self.max_age = max_age
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        origin = request.headers.get("origin")
        
        # Handle preflight requests
        if request.method == "OPTIONS":
            response = Response(status_code=204)
            self._add_cors_headers(response, origin)
            return response
        
        # Process request
        response = await call_next(request)
        
        # Add CORS headers to response
        self._add_cors_headers(response, origin)
        
        return response
    
    def _add_cors_headers(self, response: Response, origin: Optional[str]):
        """Add CORS headers to response"""
        if origin:
            # Check if origin is allowed
            if "*" in self.allow_origins or origin in self.allow_origins:
                response.headers["Access-Control-Allow-Origin"] = origin
        elif "*" in self.allow_origins:
            response.headers["Access-Control-Allow-Origin"] = "*"
        
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type, X-Requested-With"
        response.headers["Access-Control-Max-Age"] = str(self.max_age)
        
        if self.allow_credentials:
            response.headers["Access-Control-Allow-Credentials"] = "true"

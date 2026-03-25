"""
Request tracking middleware with request ID generation
"""
import uuid
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable
import time

from app.utils.logger import set_request_id, get_logger

logger = get_logger(__name__)


class RequestTrackingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to track requests with unique IDs and log request/response info
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate unique request ID
        request_id = str(uuid.uuid4())

        # Set request ID in context
        set_request_id(request_id)

        # Add request ID to request state (accessible in routes)
        request.state.request_id = request_id

        # Log incoming request
        start_time = time.time()
        logger.info(
            f"Incoming request: {request.method} {request.url.path}",
            extra={
                'extra_data': {
                    'method': request.method,
                    'path': request.url.path,
                    'query_params': dict(request.query_params),
                    'client_host': request.client.host if request.client else None,
                }
            }
        )

        try:
            # Process request
            response = await call_next(request)

            # Calculate request duration
            duration = time.time() - start_time

            # Add request ID to response headers
            response.headers['X-Request-ID'] = request_id

            # Log response
            logger.info(
                f"Request completed: {request.method} {request.url.path} - Status: {response.status_code} - Duration: {duration:.3f}s",
                extra={
                    'extra_data': {
                        'status_code': response.status_code,
                        'duration_seconds': round(duration, 3)
                    }
                }
            )

            return response

        except Exception as e:
            # Log error
            duration = time.time() - start_time
            logger.error(
                f"Request failed: {request.method} {request.url.path} - Error: {str(e)} - Duration: {duration:.3f}s",
                exc_info=True,
                extra={
                    'extra_data': {
                        'error': str(e),
                        'duration_seconds': round(duration, 3)
                    }
                }
            )
            raise


def get_request_id_from_request(request: Request) -> str:
    """
    Extract request ID from request state

    Args:
        request: FastAPI request object

    Returns:
        Request ID string
    """
    return getattr(request.state, 'request_id', 'UNKNOWN')

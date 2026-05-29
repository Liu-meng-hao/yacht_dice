import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import logging

logger = logging.getLogger(__name__)


class RequestLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        logger.info(
            f"Request: {request.method} {request.url.path} "
            f"Query: {dict(request.query_params)} "
            f"Client: {request.client.host}:{request.client.port}"
        )
        
        try:
            response: Response = await call_next(request)
            process_time = time.time() - start_time
            
            logger.info(
                f"Response: {request.method} {request.url.path} "
                f"Status: {response.status_code} "
                f"Duration: {process_time:.2f}s"
            )
            
            return response
        except Exception as e:
            process_time = time.time() - start_time
            logger.error(
                f"Error: {request.method} {request.url.path} "
                f"Exception: {str(e)} "
                f"Duration: {process_time:.2f}s"
            )
            raise
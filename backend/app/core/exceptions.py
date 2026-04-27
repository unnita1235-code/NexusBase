from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger("rag.core.exceptions")

class DomainException(Exception):
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

class NotFoundException(DomainException):
    def __init__(self, message: str):
        super().__init__(message, status_code=404)

class UnauthorizedException(DomainException):
    def __init__(self, message: str = "Unauthorized"):
        super().__init__(message, status_code=401)

def setup_exception_handlers(app: FastAPI):
    @app.exception_handler(DomainException)
    async def domain_exception_handler(request: Request, exc: DomainException):
        logger.warning(f"DomainException: {exc.message}")
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.message},
        )
    
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled Exception: {str(exc)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": "An internal server error occurred."},
        )

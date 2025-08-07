from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging

logger = logging.getLogger(__name__)


def error_response(status_code: int, message: str, *, code: str | None = None, details: dict | None = None):
    payload = {
        "success": False,
        "error": {
            "code": code or str(status_code),
            "message": message,
        }
    }
    if details:
        payload["error"]["details"] = details
    return JSONResponse(status_code=status_code, content=payload)


def register_exception_handlers(app):
    """Подключает единые обработчики ошибок к приложению FastAPI."""

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        return error_response(exc.status_code, str(exc.detail), code=str(exc.status_code))

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        logger.debug("Validation error", exc_info=True)
        return error_response(422, "Ошибка валидации запроса", code="VALIDATION_ERROR", details={"errors": exc.errors()})

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled error: {exc}", exc_info=True)
        return error_response(500, "Внутренняя ошибка сервера", code="INTERNAL_ERROR") 
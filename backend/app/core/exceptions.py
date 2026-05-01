from fastapi import Request
from fastapi.responses import JSONResponse


class AppException(Exception):
    def __init__(self, status_code: int, detail: str, code: str | None = None):
        self.status_code = status_code
        self.detail = detail
        self.code = code or f"ERR_{status_code}"


class NotFoundError(AppException):
    def __init__(self, resource: str = "Resource"):
        super().__init__(404, f"{resource} not found", "NOT_FOUND")


class ForbiddenError(AppException):
    def __init__(self, detail: str = "Forbidden"):
        super().__init__(403, detail, "FORBIDDEN")


class ConflictError(AppException):
    def __init__(self, detail: str = "Conflict"):
        super().__init__(409, detail, "CONFLICT")


class UnauthorizedError(AppException):
    def __init__(self, detail: str = "Unauthorized"):
        super().__init__(401, detail, "UNAUTHORIZED")


class ValidationError(AppException):
    def __init__(self, detail: str = "Validation error"):
        super().__init__(422, detail, "VALIDATION_ERROR")


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "code": exc.code},
    )

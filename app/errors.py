"""Errors of the API, answered as JSON with the same shape as the backend.

Every error is ``{"error": {"code": ..., "message": ..., "details": ...}}``; details
only appears when there is extra data, such as which clicked point was too far.
"""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class ApiError(Exception):
    """An expected error, turned into a JSON answer with its HTTP status."""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        *,
        details: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details
        self.headers = headers


def error_body(code: str, message: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    error: dict[str, Any] = {"code": code, "message": message}
    if details is not None:
        error["details"] = details
    return {"error": error}


def route_not_found(request: Request) -> ApiError:
    """The same 404 for an unknown route and for an endpoint that is turned off."""
    return ApiError(404, "NOT_FOUND", f"Route {request.method} {request.url.path} does not exist")


async def _api_error(_request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, ApiError)
    return JSONResponse(
        error_body(exc.code, exc.message, exc.details),
        status_code=exc.status_code,
        headers=exc.headers,
    )


async def _http_error(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, StarletteHTTPException)
    if exc.status_code == 404:
        error = route_not_found(request)
        return JSONResponse(error_body(error.code, error.message), status_code=404)
    if exc.status_code == 405:
        message = f"Method {request.method} is not allowed on {request.url.path}"
        return JSONResponse(
            error_body("METHOD_NOT_ALLOWED", message), status_code=405, headers=exc.headers
        )
    return JSONResponse(
        error_body("HTTP_ERROR", str(exc.detail)), status_code=exc.status_code, headers=exc.headers
    )


async def _validation_error(_request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    problems = [
        {
            "field": ".".join(str(part) for part in error["loc"] if part != "body"),
            "message": str(error["msg"]),
        }
        for error in exc.errors()
    ]
    message = "; ".join(f"{p['field'] or 'body'}: {p['message']}" for p in problems)
    return JSONResponse(
        error_body("INVALID_REQUEST", message, {"errors": problems}), status_code=422
    )


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ApiError, _api_error)
    app.add_exception_handler(StarletteHTTPException, _http_error)
    app.add_exception_handler(RequestValidationError, _validation_error)

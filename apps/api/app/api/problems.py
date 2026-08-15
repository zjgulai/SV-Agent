from uuid import uuid4

from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class ApiProblem(Exception):
    def __init__(self, *, status: int, code: str, title: str, detail: str) -> None:
        super().__init__(detail)
        self.status = status
        self.code = code
        self.title = title
        self.detail = detail


def _request_id(request: Request) -> str:
    candidate = request.headers.get("x-request-id", "")
    return candidate[:128] if candidate else str(uuid4())


async def api_problem_handler(request: Request, exc: ApiProblem) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status,
        media_type="application/problem+json",
        content={
            "type": f"https://reverse-engineer-mode.dev/problems/{exc.code.lower()}",
            "title": exc.title,
            "status": exc.status,
            "detail": exc.detail,
            "code": exc.code,
            "request_id": _request_id(request),
        },
    )


async def validation_problem_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        media_type="application/problem+json",
        content={
            "type": "https://reverse-engineer-mode.dev/problems/request-validation",
            "title": "Request validation failed",
            "status": 422,
            "detail": "The request body or parameters are invalid.",
            "code": "REQUEST_VALIDATION_FAILED",
            "request_id": _request_id(request),
            "errors": jsonable_encoder(exc.errors()),
        },
    )

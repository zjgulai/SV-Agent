from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from app.api.health import router as health_router
from app.api.problems import ApiProblem, api_problem_handler, validation_problem_handler
from app.api.routes.jobs import router as jobs_router
from app.api.routes.product_imports import router as product_imports_router
from app.api.routes.products import router as products_router
from app.api.routes.scripts import router as scripts_router
from app.settings import settings


def create_app() -> FastAPI:
    application = FastAPI(title=settings.app_name, version=settings.app_version)
    application.add_exception_handler(ApiProblem, api_problem_handler)  # type: ignore[arg-type]
    application.add_exception_handler(RequestValidationError, validation_problem_handler)  # type: ignore[arg-type]
    application.include_router(health_router)
    application.include_router(products_router)
    application.include_router(product_imports_router)
    application.include_router(jobs_router)
    application.include_router(scripts_router)
    return application


app = create_app()

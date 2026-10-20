"""API FastAPI. Tạo app bằng factory: `uvicorn writory.api:create_app --factory`."""

from writory.api.app import create_app

__all__ = ["create_app"]

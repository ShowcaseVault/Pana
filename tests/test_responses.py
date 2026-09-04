"""The response envelope and the exception handlers.

The app is built here rather than imported so the tests exercise the handlers
without needing a database, Redis, or the application lifespan.
"""

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel

from api.exceptions import (
    AppError,
    BadRequestError,
    ConflictError,
    ExternalServiceError,
    NotFoundError,
    UnauthorizedError,
    error_docs,
    register_exception_handlers,
)
from api.schemas.response import ApiResponse, PaginatedResponse, Pagination


class Item(BaseModel):
    name: str


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/ok", responses=error_docs(404))
    async def ok() -> ApiResponse[Item]:
        return ApiResponse(data=Item(name="x"), message="fine")

    @app.get("/raise/{kind}")
    async def raiser(kind: str) -> ApiResponse[Item]:
        raise {
            "notfound": NotFoundError("Item not found"),
            "badrequest": BadRequestError(),
            "unauthorized": UnauthorizedError(),
            "conflict": ConflictError(),
            "upstream": ExternalServiceError(),
            "app": AppError(),
        }[kind]

    @app.get("/http")
    async def http() -> ApiResponse[Item]:
        raise HTTPException(status_code=418, detail="teapot")

    @app.get("/bug")
    async def bug() -> ApiResponse[Item]:
        raise ValueError("internal detail that must not leak")

    @app.post("/validate")
    async def validate(item: Item) -> ApiResponse[Item]:
        return ApiResponse(data=item)

    @app.get("/withdata")
    async def withdata() -> ApiResponse[Item]:
        raise BadRequestError("bad", data={"field": "name"})

    return TestClient(app, raise_server_exceptions=False)


class TestSuccessEnvelope:
    def test_success_body(self, client: TestClient) -> None:
        body = client.get("/ok").json()
        assert body == {"success": True, "message": "fine", "data": {"name": "x"}}

    def test_generic_documents_payload_type(self, client: TestClient) -> None:
        """`ApiResponse[Item]` must reference Item, not a bare object."""
        schema = client.app.openapi()
        ref = schema["paths"]["/ok"]["get"]["responses"]["200"]["content"]["application/json"][
            "schema"
        ]["$ref"]
        assert ref.endswith("ApiResponse_Item_")

    def test_error_docs_documented(self, client: TestClient) -> None:
        schema = client.app.openapi()
        ref = schema["paths"]["/ok"]["get"]["responses"]["404"]["content"]["application/json"][
            "schema"
        ]["$ref"]
        assert ref.endswith("ErrorResponse")


class TestErrorEnvelope:
    @pytest.mark.parametrize(
        ("kind", "status_code"),
        [
            ("notfound", 404),
            ("badrequest", 400),
            ("unauthorized", 401),
            ("conflict", 409),
            ("upstream", 502),
            ("app", 500),
        ],
    )
    def test_status_and_shape(self, client: TestClient, kind: str, status_code: int) -> None:
        response = client.get(f"/raise/{kind}")
        assert response.status_code == status_code
        body = response.json()
        assert body["success"] is False
        assert isinstance(body["message"], str) and body["message"]
        assert "data" in body

    def test_custom_message_overrides_default(self, client: TestClient) -> None:
        assert client.get("/raise/notfound").json()["message"] == "Item not found"

    def test_default_message_used_when_omitted(self, client: TestClient) -> None:
        assert client.get("/raise/conflict").json()["message"] == "Resource already exists"

    def test_structured_data_passed_through(self, client: TestClient) -> None:
        body = client.get("/withdata").json()
        assert body["data"] == {"field": "name"}

    def test_http_exception_uses_same_envelope(self, client: TestClient) -> None:
        """A raw HTTPException must not come back as {"detail": ...}."""
        response = client.get("/http")
        assert response.status_code == 418
        assert response.json() == {"success": False, "message": "teapot", "data": None}

    def test_unhandled_error_does_not_leak(self, client: TestClient) -> None:
        response = client.get("/bug")
        assert response.status_code == 500
        assert "internal detail" not in response.text
        assert response.json()["message"] == "Internal server error"


class TestValidation:
    def test_validation_reports_fields(self, client: TestClient) -> None:
        response = client.post("/validate", json={})
        assert response.status_code == 422
        body = response.json()
        assert body["success"] is False
        assert body["data"] == [
            {"field": "body.name", "message": "Field required", "type": "missing"}
        ]

    def test_validation_omits_raw_input(self, client: TestClient) -> None:
        """`exc.errors()` carries the submitted value; it may be a secret."""
        response = client.post("/validate", json={"name": 123, "password": "hunter2"})
        assert "hunter2" not in response.text


class TestPagination:
    @pytest.mark.parametrize(
        ("total", "page_size", "expected"),
        [(0, 10, 0), (1, 10, 1), (10, 10, 1), (11, 10, 2), (25, 10, 3)],
    )
    def test_total_pages(self, total: int, page_size: int, expected: int) -> None:
        assert Pagination.build(page=1, page_size=page_size, total=total).total_pages == expected

    def test_paginated_envelope(self) -> None:
        body = PaginatedResponse[Item](
            data=Item(name="x"),
            pagination=Pagination.build(page=2, page_size=5, total=12),
        ).model_dump()
        assert body["success"] is True
        assert body["pagination"]["total_pages"] == 3

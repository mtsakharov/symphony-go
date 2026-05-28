"""Integration tests for product endpoints."""

from __future__ import annotations

from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session, sessionmaker

from app.products.models import Product


def seed_products(db_session_factory: sessionmaker[Session]) -> None:
    """Insert products for API tests."""

    products = [
        Product(name="Budget Backpack", price=Decimal("24.99")),
        Product(name="Desk Lamp", price=Decimal("49.99")),
        Product(name="Monitor Stand", price=Decimal("89.99")),
    ]
    with db_session_factory() as session:
        session.add_all(products)
        session.commit()


@pytest.mark.asyncio
async def test_list_products_filters_by_price_range(
    client: AsyncClient,
    db_session_factory: sessionmaker[Session],
) -> None:
    """Listing products should only return products within the requested range."""

    seed_products(db_session_factory)

    response = await client.get(
        "/api/v1/products",
        params={"min_price": "25.00", "max_price": "90.00"},
    )

    assert response.status_code == 200
    assert response.json()["total"] == 2
    assert [item["name"] for item in response.json()["items"]] == ["Desk Lamp", "Monitor Stand"]


@pytest.mark.asyncio
async def test_list_products_filters_with_single_bound(
    client: AsyncClient,
    db_session_factory: sessionmaker[Session],
) -> None:
    """Listing products should support a single-ended price filter."""

    seed_products(db_session_factory)

    response = await client.get("/api/v1/products", params={"max_price": "50.00"})

    assert response.status_code == 200
    assert response.json()["total"] == 2
    assert [item["name"] for item in response.json()["items"]] == ["Budget Backpack", "Desk Lamp"]


@pytest.mark.asyncio
async def test_list_products_rejects_invalid_price_range(client: AsyncClient) -> None:
    """Listing products should reject inverted price ranges."""

    response = await client.get(
        "/api/v1/products",
        params={"min_price": "100.00", "max_price": "50.00"},
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "min_price must be less than or equal to max_price"}

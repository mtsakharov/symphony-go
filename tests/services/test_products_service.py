"""Unit tests for the products service."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import Mock
from uuid import uuid4

from app.products.models import Product
from app.products.repository import ProductRepository
from app.products.service import ProductService


def build_product(*, name: str, price: str) -> Product:
    """Return a hydrated product model for service tests."""

    now = datetime.now(UTC)
    return Product(
        id=uuid4(),
        name=name,
        price=Decimal(price),
        created_at=now,
        updated_at=now,
    )


def test_list_products_applies_price_filters_and_pagination() -> None:
    """Service should forward pagination and price-range filters to the repository."""

    repository = Mock(spec=ProductRepository)
    repository.list_products.return_value = [
        build_product(name="Desk Lamp", price="49.99"),
        build_product(name="Monitor Stand", price="89.99"),
    ]
    repository.count_products.return_value = 2
    service = ProductService(repository=repository)
    session = Mock()

    response = service.list_products(
        session,
        page=2,
        limit=2,
        min_price=Decimal("25.00"),
        max_price=Decimal("90.00"),
    )

    repository.list_products.assert_called_once_with(
        session,
        offset=2,
        limit=2,
        min_price=Decimal("25.00"),
        max_price=Decimal("90.00"),
    )
    repository.count_products.assert_called_once_with(
        session,
        min_price=Decimal("25.00"),
        max_price=Decimal("90.00"),
    )
    assert response.total == 2
    assert [item.name for item in response.items] == ["Desk Lamp", "Monitor Stand"]

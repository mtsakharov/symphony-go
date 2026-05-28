"""Service layer for products."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from app.products.repository import ProductRepository
from app.products.schemas import ProductListResponse, ProductResponse


class ProductService:
    """Business logic for product retrieval."""

    def __init__(self, repository: ProductRepository | None = None) -> None:
        self.repository = repository or ProductRepository()

    def list_products(
        self,
        session: Session,
        *,
        page: int,
        limit: int,
        min_price: Decimal | None = None,
        max_price: Decimal | None = None,
    ) -> ProductListResponse:
        """Return a paginated list of products filtered by price range."""

        offset = (page - 1) * limit
        products = self.repository.list_products(
            session,
            offset=offset,
            limit=limit,
            min_price=min_price,
            max_price=max_price,
        )
        total = self.repository.count_products(
            session,
            min_price=min_price,
            max_price=max_price,
        )
        return ProductListResponse(
            items=[ProductResponse.model_validate(product) for product in products],
            page=page,
            limit=limit,
            total=total,
        )

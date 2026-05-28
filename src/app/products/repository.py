"""Repository layer for products."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.products.models import Product


class ProductRepository:
    """Persist and query products."""

    def list_products(
        self,
        session: Session,
        *,
        offset: int,
        limit: int,
        min_price: Decimal | None = None,
        max_price: Decimal | None = None,
    ) -> list[Product]:
        """Return a page of products filtered by price range."""

        statement = (
            self._build_filtered_statement(min_price=min_price, max_price=max_price)
            .order_by(Product.price.asc(), Product.id.asc())
            .offset(offset)
            .limit(limit)
        )
        return list(session.execute(statement).scalars().all())

    def count_products(
        self,
        session: Session,
        *,
        min_price: Decimal | None = None,
        max_price: Decimal | None = None,
    ) -> int:
        """Return the total number of products matching the price range."""

        filtered_products = self._build_filtered_statement(
            min_price=min_price,
            max_price=max_price,
        )
        statement = select(func.count()).select_from(filtered_products.subquery())
        return int(session.execute(statement).scalar_one())

    def _build_filtered_statement(
        self,
        *,
        min_price: Decimal | None,
        max_price: Decimal | None,
    ) -> Select[tuple[Product]]:
        """Build a filtered products query without executing it."""

        statement = select(Product)
        if min_price is not None:
            statement = statement.where(Product.price >= min_price)
        if max_price is not None:
            statement = statement.where(Product.price <= max_price)
        return statement

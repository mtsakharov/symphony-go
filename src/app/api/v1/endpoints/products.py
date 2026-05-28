"""Products read endpoints."""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.session import get_db_session
from app.products.schemas import ProductListResponse
from app.products.service import ProductService

router = APIRouter()


def get_product_service() -> ProductService:
    """Return a products service instance."""

    return ProductService()


PriceFilter = Annotated[Decimal | None, Query(ge=0, decimal_places=2)]


@router.get(
    "",
    response_model=ProductListResponse,
    summary="List products",
    description="Return a paginated list of products filtered by an optional price range.",
    operation_id="listProducts",
)
def list_products(
    session: Annotated[Session, Depends(get_db_session)],
    service: Annotated[ProductService, Depends(get_product_service)],
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    min_price: PriceFilter = None,
    max_price: PriceFilter = None,
) -> ProductListResponse:
    """List products within the requested price range."""

    if min_price is not None and max_price is not None and min_price > max_price:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="min_price must be less than or equal to max_price",
        )

    return service.list_products(
        session,
        page=page,
        limit=limit,
        min_price=min_price,
        max_price=max_price,
    )

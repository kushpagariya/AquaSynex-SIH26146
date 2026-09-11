"""Pagination utility for AquaSynex Backend.

Rules:
- page >= 1 (default: 1)
- pageSize in [1, 500] (default: 50)
- Raises InvalidPaginationError if invalid
"""

import math
from typing import Any, Dict, List, Tuple
from backend.utils.errors import InvalidPaginationError


def validate_and_normalize_pagination(
    page: int = 1,
    page_size: int = 50,
) -> Tuple[int, int]:
    """Validate and normalize pagination parameters."""
    if page < 1:
        raise InvalidPaginationError(
            f"page must be >= 1, received {page}",
            details={"field": "page", "constraint": ">= 1", "provided": page},
        )

    if page_size < 1 or page_size > 500:
        raise InvalidPaginationError(
            f"pageSize must be between 1 and 500, received {page_size}",
            details={"field": "pageSize", "constraint": "1 <= pageSize <= 500", "provided": page_size},
        )

    return page, page_size


def build_pagination_meta(
    page: int,
    page_size: int,
    total_items: int,
) -> Dict[str, Any]:
    """Build canonical PaginationMeta dictionary."""
    total_pages = math.ceil(total_items / page_size) if total_items > 0 else 0
    return {
        "page": page,
        "pageSize": page_size,
        "totalItems": total_items,
        "totalPages": total_pages,
        "hasNext": page < total_pages,
        "hasPrev": page > 1,
    }


def paginate_sequence(
    items: List[Any],
    page: int,
    page_size: int,
) -> Tuple[List[Any], Dict[str, Any]]:
    """Paginate an in-memory list and return (paged_items, pagination_meta)."""
    page, page_size = validate_and_normalize_pagination(page, page_size)
    total_items = len(items)
    start = (page - 1) * page_size
    end = start + page_size
    paged_items = items[start:end]
    meta = build_pagination_meta(page, page_size, total_items)
    return paged_items, meta

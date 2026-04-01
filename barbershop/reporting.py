from __future__ import annotations

from datetime import datetime, timedelta
from typing import Iterable, Optional, Tuple

from sqlalchemy import func

from .extensions import db
from .models import Expense, Sale, User


def resolve_date_range(
    mode: str, start_raw: Optional[str], end_raw: Optional[str]
) -> Tuple[datetime, datetime]:
    now = datetime.utcnow()
    mode = (mode or "monthly").lower()

    if mode == "daily":
        start = datetime(now.year, now.month, now.day)
        end = start + timedelta(days=1)
    elif mode == "weekly":
        start = datetime(now.year, now.month, now.day) - timedelta(days=now.weekday())
        end = start + timedelta(days=7)
    elif mode == "custom" and start_raw and end_raw:
        start = datetime.fromisoformat(start_raw)
        end = datetime.fromisoformat(end_raw) + timedelta(days=1)
    else:
        start = datetime(now.year, now.month, 1)
        if now.month == 12:
            end = datetime(now.year + 1, 1, 1)
        else:
            end = datetime(now.year, now.month + 1, 1)

    return start, end


def sales_total_between(start: datetime, end: datetime) -> float:
    result = (
        db.session.query(func.coalesce(func.sum(Sale.price), 0.0))
        .filter(Sale.date >= start, Sale.date < end)
        .scalar()
    )
    return float(result or 0.0)


def expenses_total_between(start: datetime, end: datetime) -> float:
    result = (
        db.session.query(func.coalesce(func.sum(Expense.amount), 0.0))
        .filter(Expense.date >= start, Expense.date < end)
        .scalar()
    )
    return float(result or 0.0)


def top_staff(start: datetime, end: datetime) -> Iterable[dict]:
    rows = (
        db.session.query(User.name, func.coalesce(func.sum(Sale.price), 0.0).label("total"))
        .join(Sale, Sale.staff_id == User.id)
        .filter(Sale.date >= start, Sale.date < end)
        .group_by(User.id, User.name)
        .order_by(func.sum(Sale.price).desc())
        .all()
    )
    return [{"name": r.name, "total": float(r.total)} for r in rows]


def sales_by_category(start: datetime, end: datetime) -> Iterable[dict]:
    rows = (
        db.session.query(Sale.category, func.coalesce(func.sum(Sale.price), 0.0).label("total"))
        .filter(Sale.date >= start, Sale.date < end)
        .group_by(Sale.category)
        .order_by(func.sum(Sale.price).desc())
        .all()
    )
    return [{"category": r.category, "total": float(r.total)} for r in rows]


def expenses_by_category(start: datetime, end: datetime) -> Iterable[dict]:
    rows = (
        db.session.query(
            Expense.category, func.coalesce(func.sum(Expense.amount), 0.0).label("total")
        )
        .filter(Expense.date >= start, Expense.date < end)
        .group_by(Expense.category)
        .order_by(func.sum(Expense.amount).desc())
        .all()
    )
    return [{"category": r.category, "total": float(r.total)} for r in rows]

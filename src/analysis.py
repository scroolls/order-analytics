"""Validate an order export and calculate operational retail metrics."""

from __future__ import annotations

import math
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd


REQUIRED_COLUMNS = [
    "order_id", "customer_id", "order_date", "channel", "region", "category",
    "qty", "unit_price", "promised_date", "delivered_date", "status",
]
VALID_STATUSES = {"delivered", "returned", "cancelled"}


def load_and_validate(path: Path) -> pd.DataFrame:
    raw = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    missing = set(REQUIRED_COLUMNS) - set(raw.columns)
    if missing:
        raise ValueError(f"Не хватает столбцов: {', '.join(sorted(missing))}")
    if raw.empty:
        raise ValueError("Файл не содержит заказов")

    data = raw[REQUIRED_COLUMNS].copy()
    for column in ["order_id", "customer_id", "channel", "region", "category"]:
        if data[column].str.strip().eq("").any():
            raise ValueError(f"Пустые значения в столбце {column}")
    if data["order_id"].duplicated().any():
        raise ValueError("Есть повторяющиеся order_id")
    if not data["status"].isin(VALID_STATUSES).all():
        raise ValueError("Неизвестное значение status")

    for column in ["order_date", "promised_date", "delivered_date"]:
        data[column] = pd.to_datetime(data[column], format="%Y-%m-%d", errors="coerce")
    if data[["order_date", "promised_date"]].isna().any().any():
        raise ValueError("Неверная дата заказа или обещанной доставки")
    completed = data["status"].ne("cancelled")
    if data.loc[completed, "delivered_date"].isna().any():
        raise ValueError("У завершённого заказа нет даты доставки")
    if data.loc[~completed, "delivered_date"].notna().any():
        raise ValueError("У отменённого заказа не должно быть даты доставки")
    if (data["promised_date"] < data["order_date"]).any():
        raise ValueError("Обещанная доставка раньше даты заказа")
    if (data.loc[completed, "delivered_date"] < data.loc[completed, "order_date"]).any():
        raise ValueError("Доставка раньше даты заказа")

    data["qty"] = pd.to_numeric(data["qty"], errors="coerce")
    data["unit_price"] = pd.to_numeric(data["unit_price"], errors="coerce")
    if data[["qty", "unit_price"]].isna().any().any() or not np.isfinite(data[["qty", "unit_price"]].to_numpy(dtype=float)).all():
        raise ValueError("Неверное количество или цена")
    if (data["qty"] <= 0).any() or (data["qty"] % 1 != 0).any():
        raise ValueError("Количество должно быть положительным целым числом")
    if (data["unit_price"] <= 0).any():
        raise ValueError("Цена должна быть положительной")

    data["qty"] = data["qty"].astype(int)
    data["amount"] = (data["qty"] * data["unit_price"]).round(2)
    data["month"] = data["order_date"].dt.strftime("%Y-%m")
    data["is_return"] = data["status"].eq("returned").astype(int)
    data["is_completed"] = completed.astype(int)
    data["is_late"] = (completed & (data["delivered_date"] > data["promised_date"])).astype(int)
    data["delivery_days"] = (data["delivered_date"] - data["order_date"]).dt.days
    return data


def query_metrics(data: pd.DataFrame, sql_path: Path) -> dict[str, pd.DataFrame]:
    sql_text = sql_path.read_text(encoding="utf-8")
    blocks = [block.strip() for block in sql_text.split("-- QUERY:") if block.strip()]
    metrics: dict[str, pd.DataFrame] = {}
    with sqlite3.connect(":memory:") as connection:
        sql_data = data.copy()
        for column in ["order_date", "promised_date", "delivered_date"]:
            sql_data[column] = sql_data[column].dt.strftime("%Y-%m-%d").fillna("")
        sql_data.to_sql("orders", connection, index=False, if_exists="replace")
        for block in blocks:
            name, query = block.split("\n", 1)
            metrics[name.strip()] = pd.read_sql_query(query, connection)
    return metrics


def wilson_interval(successes: int, total: int, z: float = 1.96) -> tuple[float, float]:
    if total == 0:
        return 0.0, 0.0
    proportion = successes / total
    denominator = 1 + z * z / total
    centre = (proportion + z * z / (2 * total)) / denominator
    half_width = z * math.sqrt(proportion * (1 - proportion) / total + z * z / (4 * total * total)) / denominator
    return max(0.0, centre - half_width), min(1.0, centre + half_width)


def summary(data: pd.DataFrame) -> dict[str, float | int]:
    completed = data[data["is_completed"] == 1]
    delivered = data[data["status"] == "delivered"]
    returns = int(data["is_return"].sum())
    sales = len(completed)
    low, high = wilson_interval(returns, sales)
    delivery_days = completed["delivery_days"].to_numpy(dtype=float)
    return {
        "orders": len(data),
        "completed_orders": sales,
        "cancelled_orders": int((data["status"] == "cancelled").sum()),
        "returned_orders": returns,
        "net_revenue": round(float(delivered["amount"].sum()), 2),
        "return_rate": round(returns / sales, 4) if sales else 0.0,
        "return_rate_ci_low": round(low, 4),
        "return_rate_ci_high": round(high, 4),
        "late_rate": round(float(completed["is_late"].mean()), 4) if sales else 0.0,
        "median_delivery_days": round(float(np.median(delivery_days)), 1) if sales else 0.0,
        "p90_delivery_days": round(float(np.percentile(delivery_days, 90)), 1) if sales else 0.0,
    }

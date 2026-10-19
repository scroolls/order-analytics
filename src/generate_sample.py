"""Create a reproducible sample export of retail orders."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


REGIONS = ["Москва", "Санкт-Петербург", "Казань", "Екатеринбург"]
CHANNELS = ["Сайт", "Приложение", "Партнёры"]
CATEGORIES = ["Электроника", "Дом", "Одежда", "Спорт"]
BASE_PRICES = {"Электроника": 7200, "Дом": 2600, "Одежда": 1900, "Спорт": 3400}


def generate_orders(count: int = 4000, seed: int = 20261019) -> pd.DataFrame:
    if count < 1:
        raise ValueError("Количество заказов должно быть положительным")

    rng = np.random.default_rng(seed)
    start = np.datetime64("2026-01-01", "D")
    order_days = start + rng.integers(0, 181, size=count).astype("timedelta64[D]")
    promised_days = order_days + rng.integers(2, 7, size=count).astype("timedelta64[D]")
    transit_shift = rng.choice([-1, 0, 0, 0, 1, 2, 3], size=count)
    delivery_days = promised_days + transit_shift.astype("timedelta64[D]")
    cancelled = rng.random(count) < 0.055
    late = delivery_days > promised_days
    return_probability = 0.055 + 0.075 * late
    returned = (~cancelled) & (rng.random(count) < return_probability)
    status = np.where(cancelled, "cancelled", np.where(returned, "returned", "delivered"))

    category = rng.choice(CATEGORIES, count, p=[0.24, 0.28, 0.32, 0.16])
    price_factor = rng.uniform(0.65, 1.45, count)
    unit_price = np.array([BASE_PRICES[item] for item in category]) * price_factor
    unit_price = np.round(unit_price, 2)

    frame = pd.DataFrame(
        {
            "order_id": [f"ORD-{i:06d}" for i in range(1, count + 1)],
            "customer_id": [f"CUS-{i:05d}" for i in rng.integers(1, max(2, count // 2), count)],
            "order_date": pd.to_datetime(order_days).strftime("%Y-%m-%d"),
            "channel": rng.choice(CHANNELS, count, p=[0.45, 0.43, 0.12]),
            "region": rng.choice(REGIONS, count, p=[0.42, 0.28, 0.17, 0.13]),
            "category": category,
            "qty": rng.choice([1, 2, 3, 4], count, p=[0.65, 0.24, 0.08, 0.03]),
            "unit_price": unit_price,
            "promised_date": pd.to_datetime(promised_days).strftime("%Y-%m-%d"),
            "delivered_date": pd.to_datetime(delivery_days).strftime("%Y-%m-%d"),
            "status": status,
        }
    )
    frame.loc[cancelled, "delivered_date"] = ""
    return frame.sort_values(["order_date", "order_id"]).reset_index(drop=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Сгенерировать пример выгрузки заказов")
    parser.add_argument("--output", type=Path, default=Path("data/sample_orders.csv"))
    parser.add_argument("--count", type=int, default=4000)
    parser.add_argument("--seed", type=int, default=20261019)
    args = parser.parse_args()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    generate_orders(args.count, args.seed).to_csv(args.output, index=False, encoding="utf-8-sig")
    print(f"Создан файл {args.output} ({args.count} заказов)")


if __name__ == "__main__":
    main()

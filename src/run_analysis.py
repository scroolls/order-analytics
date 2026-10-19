"""Command-line entry point for the order analysis."""

from __future__ import annotations

import argparse
from pathlib import Path

from analysis import load_and_validate, query_metrics, summary
from report import write_outputs


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description="Анализ заказов и возвратов")
    parser.add_argument("--input", type=Path, default=ROOT / "data" / "sample_orders.csv")
    parser.add_argument("--output", type=Path, default=ROOT / "reports")
    args = parser.parse_args()

    data = load_and_validate(args.input)
    metrics = query_metrics(data, ROOT / "sql" / "metrics.sql")
    result = summary(data)
    if int(metrics["monthly"]["orders"].sum()) != result["orders"]:
        raise RuntimeError("Итоги по месяцам не совпали с числом заказов")
    if abs(float(metrics["monthly"]["net_revenue"].sum()) - result["net_revenue"]) > 0.01:
        raise RuntimeError("Выручка в отчёте не совпала с общим итогом")

    write_outputs(data, metrics, result, args.output)
    print(f"Проверено заказов: {result['orders']}")
    print(f"Завершено: {result['completed_orders']}; возвратов: {result['returned_orders']}")
    print(f"Выручка после возвратов: {result['net_revenue']:,.2f} руб.")
    print(f"Доля возвратов: {result['return_rate']:.1%}")
    print(f"Отчёты сохранены в {args.output}")


if __name__ == "__main__":
    main()

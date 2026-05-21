from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime

from src.finance_data import Transaction


@dataclass(frozen=True)
class SpendingSummary:
    category: str
    total: float
    count: int
    merchants: dict[str, float]


@dataclass(frozen=True)
class SubscriptionSummary:
    merchant: str
    monthly_amount: float
    payments: int
    last_payment: datetime


@dataclass(frozen=True)
class DeliverySummary:
    total_amount: float
    total_orders: int
    late_night_orders: int
    late_night_share: float
    late_night_amount: float


@dataclass(frozen=True)
class CashflowSummary:
    income: float
    expenses: float
    net: float


@dataclass(frozen=True)
class SavingsOpportunity:
    category: str
    estimated_monthly_saving: float
    reason: str
    action: str


def expense_amount(transaction: Transaction) -> float:
    return abs(transaction.amount) if transaction.amount < 0 else 0.0


def spending_for_category(
    transactions: list[Transaction],
    category: str,
    start: datetime | None = None,
    end: datetime | None = None,
) -> SpendingSummary:
    total = 0.0
    count = 0
    merchants: dict[str, float] = defaultdict(float)

    for transaction in transactions:
        if transaction.category != category:
            continue
        if transaction.amount >= 0:
            continue
        if start is not None and transaction.date < start:
            continue
        if end is not None and transaction.date > end:
            continue

        amount = expense_amount(transaction)
        total += amount
        count += 1
        merchants[transaction.merchant] += amount

    return SpendingSummary(
        category=category,
        total=round(total, 2),
        count=count,
        merchants={merchant: round(amount, 2) for merchant, amount in merchants.items()},
    )


def top_spending_categories(
    transactions: list[Transaction],
    limit: int = 5,
    start: datetime | None = None,
    end: datetime | None = None,
) -> list[tuple[str, float]]:
    totals: dict[str, float] = defaultdict(float)

    for transaction in transactions:
        if transaction.amount >= 0:
            continue
        if start is not None and transaction.date < start:
            continue
        if end is not None and transaction.date > end:
            continue

        totals[transaction.category] += expense_amount(transaction)

    sorted_totals = sorted(totals.items(), key=lambda item: item[1], reverse=True)
    return [(category, round(total, 2)) for category, total in sorted_totals[:limit]]


def subscriptions_summary(transactions: list[Transaction]) -> dict[str, SubscriptionSummary]:
    groups: dict[str, list[Transaction]] = defaultdict(list)
    for transaction in transactions:
        if transaction.category == "subscriptions" and transaction.recurring and transaction.amount < 0:
            groups[transaction.merchant].append(transaction)

    summaries: dict[str, SubscriptionSummary] = {}
    for merchant, payments in groups.items():
        total = sum(expense_amount(payment) for payment in payments)
        last_payment = max(payment.date for payment in payments)
        summaries[merchant] = SubscriptionSummary(
            merchant=merchant,
            monthly_amount=round(total / len(payments), 2),
            payments=len(payments),
            last_payment=last_payment,
        )
    return summaries


def suspicious_transactions(transactions: list[Transaction]) -> list[Transaction]:
    suspicious_merchants = {"booking.com", "aliexpress"}
    result: list[Transaction] = []

    for transaction in transactions:
        if transaction.account != "credit_card":
            continue
        if transaction.amount >= 0:
            continue
        if transaction.merchant.lower() in suspicious_merchants:
            result.append(transaction)

    return sorted(result, key=lambda transaction: transaction.date)


def delivery_late_night_summary(transactions: list[Transaction]) -> DeliverySummary:
    delivery_transactions = [
        transaction
        for transaction in transactions
        if transaction.category == "delivery" and transaction.amount < 0
    ]
    late_night_transactions = [
        transaction
        for transaction in delivery_transactions
        if transaction.date.hour >= 21
    ]

    total_amount = sum(expense_amount(transaction) for transaction in delivery_transactions)
    late_night_amount = sum(expense_amount(transaction) for transaction in late_night_transactions)
    total_orders = len(delivery_transactions)
    late_night_orders = len(late_night_transactions)
    late_night_share = late_night_orders / total_orders if total_orders else 0.0

    return DeliverySummary(
        total_amount=round(total_amount, 2),
        total_orders=total_orders,
        late_night_orders=late_night_orders,
        late_night_share=round(late_night_share, 2),
        late_night_amount=round(late_night_amount, 2),
    )


def cashflow_for_period(
    transactions: list[Transaction],
    start: datetime | None = None,
    end: datetime | None = None,
) -> CashflowSummary:
    income = 0.0
    expenses = 0.0

    for transaction in transactions:
        if start is not None and transaction.date < start:
            continue
        if end is not None and transaction.date > end:
            continue

        if transaction.amount > 0:
            income += transaction.amount
        elif transaction.amount < 0:
            expenses += expense_amount(transaction)

    return CashflowSummary(
        income=round(income, 2),
        expenses=round(expenses, 2),
        net=round(income - expenses, 2),
    )


def covered_months(transactions: list[Transaction]) -> int:
    months = {(transaction.date.year, transaction.date.month) for transaction in transactions}
    return max(len(months), 1)


def savings_opportunities(transactions: list[Transaction]) -> list[SavingsOpportunity]:
    opportunities: list[SavingsOpportunity] = []
    month_count = covered_months(transactions)

    delivery = delivery_late_night_summary(transactions)
    if delivery.total_amount > 0:
        delivery_monthly_amount = delivery.total_amount / month_count
        opportunities.append(
            SavingsOpportunity(
                category="delivery",
                estimated_monthly_saving=round(delivery_monthly_amount * 0.5, 2),
                reason=(
                    f"Delivery витрати: ~${delivery_monthly_amount:.2f}/міс; "
                    f"{delivery.late_night_share:.0%} замовлень після 21:00."
                ),
                action="Скоротити delivery вдвічі або прибрати пізні імпульсні замовлення.",
            )
        )

    subscriptions = subscriptions_summary(transactions)
    if "Sportlife" in subscriptions:
        sportlife = subscriptions["Sportlife"]
        opportunities.append(
            SavingsOpportunity(
                category="subscriptions",
                estimated_monthly_saving=sportlife.monthly_amount,
                reason="Sportlife виглядає як підписка, яку варто перевірити окремо.",
                action="Перевірити, чи підписка Sportlife ще потрібна, і скасувати її, якщо ні.",
            )
        )

    coffee = spending_for_category(transactions, "coffee")
    if coffee.total > 0:
        coffee_monthly_amount = coffee.total / month_count
        opportunities.append(
            SavingsOpportunity(
                category="coffee",
                estimated_monthly_saving=round(coffee_monthly_amount * 0.4, 2),
                reason=f"Кава поза домом: ~${coffee_monthly_amount:.2f}/міс.",
                action="Залишити ритуал, але 2 дні на тиждень готувати каву вдома.",
            )
        )

    return sorted(opportunities, key=lambda item: item.estimated_monthly_saving, reverse=True)

from datetime import datetime

from src.finance_data import Transaction
from src.router import route_question
from src.tools import (
    cashflow_for_period,
    delivery_late_night_summary,
    savings_opportunities,
    spending_for_category,
    subscriptions_summary,
    suspicious_transactions,
    top_spending_categories,
)


def tx(date, merchant, amount, category, account="main_debit", recurring=False):
    return Transaction(
        date=datetime.fromisoformat(date),
        merchant=merchant,
        amount=amount,
        currency="USD",
        category=category,
        account=account,
        recurring=recurring,
    )


def test_spending_for_category_sums_only_expenses_inside_date_range():
    transactions = [
        tx("2025-06-01T08:00", "Aroma Kava", -4.5, "coffee"),
        tx("2025-06-02T08:00", "Blue Bottle", -5.5, "coffee"),
        tx("2025-06-03T12:00", "ATB", -40.0, "groceries"),
        tx("2025-07-01T08:00", "Aroma Kava", -6.0, "coffee"),
        tx("2025-06-04T09:00", "Refund", 3.0, "coffee"),
    ]

    result = spending_for_category(
        transactions,
        category="coffee",
        start=datetime(2025, 6, 1),
        end=datetime(2025, 6, 30, 23, 59),
    )

    assert result.total == 10.0
    assert result.count == 2
    assert result.merchants == {"Aroma Kava": 4.5, "Blue Bottle": 5.5}


def test_top_spending_categories_excludes_income_and_sorts_descending():
    transactions = [
        tx("2025-06-01T08:00", "Salary", 3000.0, "salary"),
        tx("2025-06-02T12:00", "ATB", -100.0, "groceries"),
        tx("2025-06-03T20:00", "Glovo", -80.0, "delivery"),
        tx("2025-06-04T10:00", "Silpo", -30.0, "groceries"),
        tx("2025-06-05T08:00", "Aroma Kava", -15.0, "coffee"),
    ]

    result = top_spending_categories(transactions, limit=2)

    assert result == [("groceries", 130.0), ("delivery", 80.0)]


def test_subscriptions_summary_groups_recurring_expenses_by_merchant():
    transactions = [
        tx("2025-06-01T19:00", "Spotify", -5.0, "subscriptions", recurring=True),
        tx("2025-07-01T19:00", "Spotify", -5.0, "subscriptions", recurring=True),
        tx("2025-06-10T10:00", "Netflix", -12.0, "subscriptions", recurring=True),
        tx("2025-06-11T10:00", "Cinema", -20.0, "entertainment", recurring=False),
    ]

    result = subscriptions_summary(transactions)

    assert result["Spotify"].monthly_amount == 5.0
    assert result["Spotify"].payments == 2
    assert result["Netflix"].monthly_amount == 12.0


def test_suspicious_transactions_returns_large_foreign_credit_card_expenses():
    transactions = [
        tx("2025-12-03T15:00", "Booking.com", -890.0, "travel", account="credit_card"),
        tx("2025-12-04T11:00", "AliExpress", -220.0, "shopping", account="credit_card"),
        tx("2025-12-05T12:00", "ATB", -40.0, "groceries", account="main_debit"),
    ]

    result = suspicious_transactions(transactions)

    assert [item.merchant for item in result] == ["Booking.com", "AliExpress"]


def test_route_question_maps_simple_ukrainian_questions_to_intents():
    assert route_question("Скільки витратив на каву минулого тижня?").intent == "category_spending"
    assert route_question("Топ-5 категорій витрат за червень").intent == "top_categories"
    assert route_question("На які підписки я витрачаюсь?").intent == "subscriptions"
    assert route_question("Я не робив транзакцію Booking.com").intent == "fraud"


def test_delivery_late_night_summary_counts_orders_after_21_00():
    transactions = [
        tx("2025-06-01T20:30", "Glovo", -30.0, "delivery"),
        tx("2025-06-02T21:00", "Bolt Food", -20.0, "delivery"),
        tx("2025-06-03T23:10", "Uber Eats", -40.0, "delivery"),
        tx("2025-06-04T12:00", "ATB", -50.0, "groceries"),
    ]

    result = delivery_late_night_summary(transactions)

    assert result.total_amount == 90.0
    assert result.total_orders == 3
    assert result.late_night_orders == 2
    assert result.late_night_share == 0.67
    assert result.late_night_amount == 60.0


def test_cashflow_for_period_separates_income_expenses_and_net():
    transactions = [
        tx("2025-06-01T09:00", "Salary", 3000.0, "salary"),
        tx("2025-06-02T12:00", "ATB", -200.0, "groceries"),
        tx("2025-06-03T19:00", "Netflix", -12.0, "subscriptions"),
        tx("2025-07-01T12:00", "ATB", -100.0, "groceries"),
    ]

    result = cashflow_for_period(
        transactions,
        start=datetime(2025, 6, 1),
        end=datetime(2025, 6, 30, 23, 59),
    )

    assert result.income == 3000.0
    assert result.expenses == 212.0
    assert result.net == 2788.0


def test_savings_opportunities_returns_concrete_actions_from_data():
    transactions = [
        tx("2025-06-01T22:30", "Glovo", -40.0, "delivery"),
        tx("2025-06-02T22:30", "Bolt Food", -60.0, "delivery"),
        tx("2025-06-03T08:30", "Aroma Kava", -5.0, "coffee"),
        tx("2025-06-04T08:30", "Blue Bottle", -5.0, "coffee"),
        tx("2025-06-05T10:00", "Sportlife", -15.0, "subscriptions", recurring=True),
        tx("2025-06-06T10:00", "Spotify", -5.0, "subscriptions", recurring=True),
    ]

    result = savings_opportunities(transactions)

    assert result[0].category == "delivery"
    assert result[0].estimated_monthly_saving == 50.0
    assert any(item.category == "subscriptions" and item.estimated_monthly_saving == 15.0 for item in result)
    assert any(item.category == "coffee" and item.estimated_monthly_saving == 4.0 for item in result)


def test_savings_opportunities_normalizes_variable_spending_to_monthly_estimate():
    transactions = [
        tx("2025-06-01T22:30", "Glovo", -100.0, "delivery"),
        tx("2025-07-01T22:30", "Glovo", -300.0, "delivery"),
        tx("2025-06-03T08:30", "Aroma Kava", -50.0, "coffee"),
        tx("2025-07-03T08:30", "Aroma Kava", -150.0, "coffee"),
    ]

    result = savings_opportunities(transactions)

    assert result[0].category == "delivery"
    assert result[0].estimated_monthly_saving == 100.0
    assert next(item for item in result if item.category == "coffee").estimated_monthly_saving == 40.0

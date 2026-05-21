from __future__ import annotations

from enum import StrEnum


class Intent(StrEnum):
    CATEGORY_SPENDING = "category_spending"
    TOP_CATEGORIES = "top_categories"
    SUBSCRIPTIONS = "subscriptions"
    DELIVERY = "delivery"
    CASHFLOW = "cashflow"
    SAVINGS = "savings"
    FRAUD = "fraud"
    UNKNOWN = "unknown"


class Period(StrEnum):
    LAST_7_DAYS = "last_7_days"
    CURRENT_MONTH = "current_month"


class Category(StrEnum):
    COFFEE = "coffee"
    GROCERIES = "groceries"
    RESTAURANTS = "restaurants"
    DELIVERY = "delivery"
    TRANSPORT = "transport"
    ENTERTAINMENT = "entertainment"
    SHOPPING = "shopping"
    HEALTH = "health"
    SUBSCRIPTIONS = "subscriptions"
    UTILITIES = "utilities"
    SALARY = "salary"
    CREDIT_PAYMENT = "credit_payment"
    TRAVEL = "travel"


class ToolName(StrEnum):
    SPENDING_FOR_CATEGORY = "spending_for_category"
    TOP_SPENDING_CATEGORIES = "top_spending_categories"
    SUBSCRIPTIONS_SUMMARY = "subscriptions_summary"
    DELIVERY_LATE_NIGHT_SUMMARY = "delivery_late_night_summary"
    CASHFLOW_FOR_PERIOD = "cashflow_for_period"
    SAVINGS_OPPORTUNITIES = "savings_opportunities"
    SUSPICIOUS_TRANSACTIONS = "suspicious_transactions"

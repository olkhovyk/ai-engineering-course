from src.constants import Category, Intent, ToolName


def test_intent_constants_are_string_compatible():
    assert Intent.CATEGORY_SPENDING == "category_spending"
    assert Intent.SAVINGS == "savings"
    assert str(Intent.FRAUD) == "fraud"


def test_category_and_tool_constants_are_string_compatible():
    assert Category.COFFEE == "coffee"
    assert ToolName.SPENDING_FOR_CATEGORY == "spending_for_category"

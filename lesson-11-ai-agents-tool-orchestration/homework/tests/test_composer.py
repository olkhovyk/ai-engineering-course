from src.composer import LLMComposer, TemplateComposer
from src.tools import SpendingSummary


class FakeComposerClient:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def complete(self, system_prompt, user_prompt):
        self.calls.append((system_prompt, user_prompt))
        return self.response


def test_template_composer_formats_category_spending_result():
    composer = TemplateComposer()
    summary = SpendingSummary(
        category="coffee",
        total=19.81,
        count=4,
        merchants={"Aroma Kava": 10.0, "Blue Bottle": 9.81},
    )

    answer = composer.compose(
        question="Скільки я витратив на каву?",
        intent="category_spending",
        tool_name="spending_for_category",
        tool_result=summary,
    )

    assert answer == "coffee: $19.81 за останні 7 днів (4 транзакцій)."


def test_llm_composer_uses_grounded_facts_in_prompt():
    client = FakeComposerClient("Ти витратив на каву $19.81 за 4 транзакції.")
    composer = LLMComposer(client=client)
    summary = SpendingSummary(
        category="coffee",
        total=19.81,
        count=4,
        merchants={"Aroma Kava": 10.0, "Blue Bottle": 9.81},
    )

    answer = composer.compose(
        question="Скільки я витратив на каву?",
        intent="category_spending",
        tool_name="spending_for_category",
        tool_result=summary,
    )

    assert answer == "Ти витратив на каву $19.81 за 4 транзакції."
    assert "Do not invent numbers" in client.calls[0][0]
    assert '"total": 19.81' in client.calls[0][1]
    assert '"count": 4' in client.calls[0][1]


def test_llm_composer_falls_back_to_template_when_client_fails():
    class FailingClient:
        def complete(self, system_prompt, user_prompt):
            raise RuntimeError("network error")

    composer = LLMComposer(client=FailingClient())
    summary = SpendingSummary(category="coffee", total=19.81, count=4, merchants={})

    answer = composer.compose(
        question="Скільки я витратив на каву?",
        intent="category_spending",
        tool_name="spending_for_category",
        tool_result=summary,
    )

    assert answer == "coffee: $19.81 за останні 7 днів (4 транзакцій)."

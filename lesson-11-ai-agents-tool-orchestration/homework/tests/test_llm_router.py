from src.llm_router import LLMRouter, RouterLLMClient, parse_route_json
from src.routing import Route


class FakeLLMClient(RouterLLMClient):
    def __init__(self, response):
        self.response = response
        self.calls = []

    def complete(self, system_prompt, user_prompt):
        self.calls.append((system_prompt, user_prompt))
        return self.response


def test_parse_route_json_accepts_valid_intent_and_category():
    route = parse_route_json('{"intent": "category_spending", "category": "coffee"}')

    assert route == Route(intent="category_spending", category="coffee")


def test_llm_router_routes_typo_question_from_structured_response():
    client = FakeLLMClient('{"intent": "category_spending", "category": "coffee"}')
    router = LLMRouter(client=client)

    route = router.route("Скільки я витратив на кавву?")

    assert route == Route(intent="category_spending", category="coffee")
    assert "valid intents" in client.calls[0][0]
    assert "кавву" in client.calls[0][1]


def test_llm_router_falls_back_to_rule_based_router_on_invalid_json():
    client = FakeLLMClient("not json")
    router = LLMRouter(client=client)

    route = router.route("Скільки витратив на каву?")

    assert route == Route(intent="category_spending", category="coffee")


def test_llm_router_rejects_unknown_intent_from_model():
    client = FakeLLMClient('{"intent": "buy_stocks", "category": null}')
    router = LLMRouter(client=client)

    route = router.route("Купи мені акції Apple")

    assert route == Route(intent="unknown")

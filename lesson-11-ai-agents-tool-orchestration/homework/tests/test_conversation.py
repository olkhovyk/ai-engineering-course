from src.constants import Category, Intent, Period
from src.conversation import ContextualRouter, ConversationContext
from src.routing import Route


def test_context_resolves_month_followup_from_previous_category_route():
    context = ConversationContext()
    context.remember(Route(intent=Intent.CATEGORY_SPENDING, category=Category.COFFEE))

    route = context.resolve_followup("А за місяць?")

    assert route == Route(
        intent=Intent.CATEGORY_SPENDING,
        category=Category.COFFEE,
        period=Period.CURRENT_MONTH,
    )


def test_context_does_not_resolve_followup_without_previous_route():
    context = ConversationContext()

    assert context.resolve_followup("А за місяць?") is None


class FakeRouter:
    def route(self, question):
        return Route(intent=Intent.UNKNOWN)


def test_contextual_router_uses_context_before_base_router():
    context = ConversationContext(last_route=Route(intent=Intent.CATEGORY_SPENDING, category=Category.COFFEE))
    router = ContextualRouter(base_router=FakeRouter(), context=context)

    route = router.route("А за місяць?")

    assert route == Route(
        intent=Intent.CATEGORY_SPENDING,
        category=Category.COFFEE,
        period=Period.CURRENT_MONTH,
    )
    assert router.last_route == route

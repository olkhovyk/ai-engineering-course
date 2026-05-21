from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from src.cli import build_agent, build_composer, build_router
from src.conversation import ContextualRouter, ConversationContext
from src.env import load_project_env
from src.eval_runner import DEFAULT_GOLDEN_PATH, DEFAULT_OUTPUT_PATH, run_eval, summarize
from src.finance_data import load_transactions
from src.langsmith_tracing import flush_langsmith
from src.ui_helpers import langsmith_status, metrics_row, tool_call_rows, trace_rows


BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "starter" / "data" / "transactions.csv"


@st.cache_data
def load_data():
    return load_transactions(DATA_PATH)


def main() -> None:
    load_project_env()
    st.set_page_config(page_title="Personal Finance Crew", layout="wide")
    if "conversation_context" not in st.session_state:
        st.session_state.conversation_context = ConversationContext()

    st.title("Personal Finance Crew")

    with st.sidebar:
        st.header("Run settings")
        architecture = st.selectbox("Architecture", ["baseline", "crew"], index=1)
        router_name = st.selectbox("Router", ["rule", "llm"], index=0)
        composer_name = st.selectbox("Composer", ["template", "llm"], index=0)
        st.divider()
        st.caption("LLM options use OpenRouter settings from .env.")
        st.caption(f"LangSmith tracing: {langsmith_status()}")
        if st.button("Clear conversation"):
            st.session_state.conversation_context = ConversationContext()

    transactions = load_data()

    chat_tab, eval_tab = st.tabs(["Chat", "Eval"])

    with chat_tab:
        question = st.text_area(
            "Question",
            value="Де можна зекономити цього місяця?",
            height=120,
        )
        submitted = st.button("Submit", type="primary")

        if submitted:
            try:
                router = ContextualRouter(
                    build_router(router_name),
                    st.session_state.conversation_context,
                )
                composer = build_composer(composer_name)
                agent = build_agent(
                    architecture,
                    transactions,
                    router=router,
                    composer=composer,
                )
                result = agent.run(question)
                if router.last_route is not None:
                    st.session_state.conversation_context.remember(router.last_route)
                flush_langsmith()
            except Exception as error:
                st.error(str(error))
            else:
                st.subheader("Answer")
                st.write(result.answer)

                st.subheader("Metrics")
                st.dataframe(pd.DataFrame([metrics_row(result)]), use_container_width=True)

                left, right = st.columns(2)
                with left:
                    st.subheader("Tool Calls")
                    rows = tool_call_rows(result)
                    st.dataframe(pd.DataFrame(rows), use_container_width=True) if rows else st.info("No tool calls")
                with right:
                    st.subheader("Trace")
                    st.dataframe(pd.DataFrame(trace_rows(result)), use_container_width=True)

                with st.expander("Raw result"):
                    st.json(
                        {
                            "architecture": result.architecture,
                            "intent": result.intent,
                            "latency_ms": result.latency_ms,
                            "answer": result.answer,
                            "tool_calls": tool_call_rows(result),
                            "trace": trace_rows(result),
                        }
                    )

    with eval_tab:
        st.write("Run golden set against baseline and crew with the selected router/composer.")
        run_clicked = st.button("Run eval")

        if run_clicked:
            try:
                rows = run_eval(
                    transactions=transactions,
                    golden_path=DEFAULT_GOLDEN_PATH,
                    output_path=DEFAULT_OUTPUT_PATH,
                    architectures=["baseline", "crew"],
                    router_name=router_name,
                    composer_name=composer_name,
                )
                flush_langsmith()
            except Exception as error:
                st.error(str(error))
            else:
                st.subheader("Summary")
                summary_lines = summarize(rows).splitlines()
                summary_rows = [line.split(",") for line in summary_lines[1:]]
                st.dataframe(
                    pd.DataFrame(
                        summary_rows,
                        columns=["architecture", "cases", "intent_accuracy", "tool_accuracy", "avg_latency_ms"],
                    ),
                    use_container_width=True,
                )

                st.subheader("Results")
                st.dataframe(pd.DataFrame(rows), use_container_width=True)
                st.caption(f"Wrote {DEFAULT_OUTPUT_PATH}")


if __name__ == "__main__":
    main()

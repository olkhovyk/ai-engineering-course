"""Invoice Extraction: Regex + LLM Hybrid Demo.

Shows how preprocessing (regex extraction) reduces LLM costs
while maintaining accuracy.
"""

import json
import os

import streamlit as st
from dotenv import load_dotenv

from loader import list_invoices, extract_text
from pipeline import extract_invoice
from regex_extractor import regex_extract

load_dotenv()


def main():
    st.set_page_config(page_title="Invoice Extraction", page_icon="\U0001f4c4", layout="wide")
    st.title("\U0001f4c4 Invoice Extraction: PDF \u2192 JSON")
    st.caption(
        "Compare two approaches: send everything to LLM vs extract with regex first, "
        "then LLM fills the gaps. Same accuracy, lower cost."
    )

    api_key = os.environ.get("OPENAI_KEY") or os.environ.get("OPENAI_API_KEY") or ""
    if not api_key:
        st.error("Set OPENAI_KEY in .env file")
        return

    # --- Sidebar ---
    with st.sidebar:
        st.header("Invoice")
        invoices = list_invoices()
        invoice_names = [inv["file"] for inv in invoices]

        selected = st.selectbox("Select sample invoice", invoice_names)
        uploaded = st.file_uploader("Or upload PDF", type=["pdf"])

        st.divider()
        st.header("Mode")
        mode = st.radio(
            "Extraction mode",
            ["Side-by-side comparison", "LLM only", "Hybrid (regex + LLM)"],
            help="Side-by-side runs both and compares cost/speed/accuracy.",
        )

    # --- Load invoice text ---
    if uploaded:
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(uploaded.read())
            text = extract_text(f.name)
    else:
        inv = next((i for i in invoices if i["file"] == selected), None)
        text = inv["text"] if inv else ""

    if not text:
        st.warning("No invoice text extracted.")
        return

    # Show raw text
    with st.expander("Raw invoice text", expanded=False):
        st.text(text)

    # --- Regex preview ---
    st.subheader("Step 1: Regex Extraction (free, instant)")
    regex_result = regex_extract(text)

    col_r1, col_r2 = st.columns(2)
    with col_r1:
        st.metric("Fields found by regex", f"{regex_result['fields_found']}/{regex_result['fields_total']}")
    with col_r2:
        pct = regex_result['fields_found'] / regex_result['fields_total'] * 100
        st.metric("Coverage", f"{pct:.0f}%")

    # Show what regex found
    conf_display = {}
    for field, conf in regex_result["confidence"].items():
        val = regex_result["extracted"].get(field, "---")
        icon = {"HIGH": "\u2705", "MEDIUM": "\u26a0\ufe0f", "LOW": "\u26a0\ufe0f", "NONE": "\u274c"}[conf]
        conf_display[field] = f"{icon} {val}" if conf != "NONE" else f"{icon} not found"
    st.dataframe({"Field": list(conf_display.keys()), "Value": list(conf_display.values())}, use_container_width=True)

    st.divider()

    # --- LLM Extraction ---
    st.subheader("Step 2: LLM Extraction")

    run = st.button("Extract with LLM", type="primary")
    if not run:
        return

    if mode == "Side-by-side comparison":
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### LLM Only")
            with st.spinner("Full LLM extraction..."):
                result_full = extract_invoice(text, "llm_only", api_key)
            st.metric("Tokens used", result_full["tokens_used"])
            st.metric("Time", f"{result_full['time_seconds']}s")
            cost_full = result_full["tokens_used"] * 0.00000015  # gpt-4o-mini input
            st.metric("Est. cost", f"${cost_full:.4f}")
            st.json(result_full["data"])

        with col2:
            st.markdown("### Hybrid (Regex + LLM)")
            with st.spinner("Hybrid extraction..."):
                result_hybrid = extract_invoice(text, "hybrid", api_key)
            st.metric("Tokens used", result_hybrid["tokens_used"],
                       delta=result_hybrid["tokens_used"] - result_full["tokens_used"])
            st.metric("Time", f"{result_hybrid['time_seconds']}s",
                       delta=f"{result_hybrid['time_seconds'] - result_full['time_seconds']:.1f}s")
            cost_hybrid = result_hybrid["tokens_used"] * 0.00000015
            st.metric("Est. cost", f"${cost_hybrid:.4f}",
                       delta=f"${cost_hybrid - cost_full:.4f}")
            st.json(result_hybrid["data"])

        # Summary
        st.divider()
        st.subheader("Comparison")
        savings_tokens = result_full["tokens_used"] - result_hybrid["tokens_used"]
        savings_pct = savings_tokens / result_full["tokens_used"] * 100 if result_full["tokens_used"] else 0
        savings_time = result_full["time_seconds"] - result_hybrid["time_seconds"]

        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Token savings", f"{savings_pct:.0f}%")
        with c2:
            st.metric("Time saved", f"{savings_time:.1f}s")
        with c3:
            st.metric("Regex pre-extracted", f"{result_hybrid.get('regex_fields_found', 0)} fields")

    else:
        m = "llm_only" if mode == "LLM only" else "hybrid"
        with st.spinner("Extracting..."):
            result = extract_invoice(text, m, api_key)
        st.metric("Tokens used", result["tokens_used"])
        st.metric("Time", f"{result['time_seconds']}s")
        st.json(result["data"])


if __name__ == "__main__":
    main()

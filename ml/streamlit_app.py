"""
A tiny Streamlit form to test the lead scorer by hand. You type in one caller's
details, we work out the same features the model was trained on, load the pickle
and show the P(buy) plus a quick High/Medium/Low call. Run it with:
    .venv/bin/streamlit run streamlit_app.py
"""

import pickle
import pandas as pd
import streamlit as st

import priors

MODEL_PKL = "lead_scorer.pkl"
BASE_RATE = 0.015           # ~1.5% of the list converts
BHK_ORDER = {"1BHK": 1, "2BHK": 2, "3BHK": 3, "4BHK+": 4}
INTENT_MAP = {"End-use (self use)": 0, "Investment": 1}
LAKH = 100_000


@st.cache_resource
def load_model():
    with open(MODEL_PKL, "rb") as f:
        return pickle.load(f)


def budget_band_match(stated_budget, property_ticket):
    """1 if the flat's price falls inside the budget band the buyer is aiming at."""
    for _, (lo, hi) in priors.BUDGET_BANDS:
        if lo <= stated_budget <= hi:
            return int(lo <= property_ticket <= hi)
    return int(property_ticket >= priors.BUDGET_BANDS[-1][1][0])   # above top band


st.set_page_config(page_title="Lead Scorer", page_icon="📞")
st.title("📞 Real-estate Lead Scorer")
st.caption("Enter a caller's details and the model returns their probability of buying.")

obj = load_model()
model, features = obj["model"], obj["features"]

with st.form("lead"):
    c1, c2 = st.columns(2)
    income_l = c1.number_input("Annual household income (₹ Lakh)", 3.0, 200.0, 18.0, 1.0)
    budget_l = c2.number_input("Stated budget (₹ Lakh)", 20.0, 1000.0, 90.0, 5.0)
    price_l = c1.number_input("Flat price / ticket (₹ Lakh)", 20.0, 1000.0, 85.0, 5.0)
    intent_lbl = c2.selectbox("Buying intent", list(INTENT_MAP))
    bhk_pref = c1.selectbox("Preferred BHK", list(BHK_ORDER), index=2)
    bhk_enq = c2.selectbox("BHK of the flat enquired", list(BHK_ORDER), index=2)
    submitted = st.form_submit_button("Score this lead")

if submitted:
    income, budget, price = income_l * LAKH, budget_l * LAKH, price_l * LAKH

    row = {
        "affordability_ratio": price / income,
        "annual_income": income,
        "price_to_budget": price / budget,
        "budget_match": budget_band_match(budget, price),
        "bhk_match": int(BHK_ORDER[bhk_pref] == BHK_ORDER[bhk_enq]),
        "intent": INTENT_MAP[intent_lbl],
    }
    p = float(model.predict_proba(pd.DataFrame([row])[features])[:, 1][0])

    st.subheader("Result")
    m1, m2 = st.columns(2)
    m1.metric("Probability of buying", f"{p*100:.2f}%")
    m2.metric("vs base rate (1.5%)", f"{p/BASE_RATE:.1f}× ")

    if p >= 3 * BASE_RATE:
        st.success("🔥 HIGH priority — call first.")
    elif p >= BASE_RATE:
        st.warning("🟡 MEDIUM priority — call after the hot leads.")
    else:
        st.info("🔵 LOW priority — deprioritise.")

    with st.expander("Features the model saw"):
        st.write({k: round(v, 3) for k, v in row.items()})

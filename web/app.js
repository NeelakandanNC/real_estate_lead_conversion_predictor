// Grabs the form values, asks /api/score for the probability, and draws the result.
const form = document.getElementById("lead-form");
const result = document.getElementById("result");

const fmt = (n) => (n * 100).toFixed(2) + "%";
const labels = {
  affordability_ratio: "Affordability ratio (price ÷ income)",
  annual_income: "Annual income (₹)",
  price_to_budget: "Price ÷ stated budget",
  budget_match: "Within stated budget?",
  bhk_match: "BHK matches preference?",
  intent: "Investment intent?",
};

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const input = Object.fromEntries(new FormData(form).entries());
  result.innerHTML = `<div class="placeholder">Scoring…</div>`;

  try {
    const r = await fetch("/api/score", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    });
    const d = await r.json();
    if (!r.ok) throw new Error(d.error || "request failed");
    render(d);
  } catch (err) {
    result.innerHTML = `<div class="placeholder">⚠️ ${err.message}</div>`;
  }
});

function render(d) {
  // cap the bar at ~8x base rate so the fill stays readable
  const fill = Math.min(100, (d.multiple / 8) * 100);
  const feats = Object.entries(d.features)
    .map(([k, v]) => {
      const val = k === "annual_income" ? "₹" + Number(v).toLocaleString("en-IN")
        : Number.isInteger(v) ? (v ? "Yes" : "No") : v.toFixed(2);
      return `<div><span>${labels[k] || k}</span><span>${val}</span></div>`;
    })
    .join("");

  result.innerHTML = `
    <div class="score-label">Probability of buying</div>
    <div class="score-big">${fmt(d.p_buy)}</div>
    <span class="badge ${d.priority}">${d.priority} PRIORITY</span>
    <div class="multiple">${d.multiple.toFixed(1)}× the average caller (base rate ${fmt(d.base_rate)})</div>
    <div class="bar"><span style="width:${fill}%"></span></div>
    <div class="bar-cap"><span>base ${fmt(d.base_rate)}</span><span>8× base</span></div>
    <div class="feats"><h4>What the model saw</h4>${feats}</div>`;
}

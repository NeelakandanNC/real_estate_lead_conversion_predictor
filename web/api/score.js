// Vercel serverless function: scores one lead. Pure JavaScript, ZERO dependencies
// (no ML runtime) so the function stays tiny and well under Vercel's size limit.
// A gradient-boosted model is just: walk each decision tree, sum the leaf values,
// then map that raw score through the isotonic calibration curve. model.json holds
// the trees + curve, exported from LightGBM by ml/export_web_model.py.

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const MODEL_DIR = fs.existsSync(path.join(process.cwd(), "model"))
  ? path.join(process.cwd(), "model")
  : path.join(__dirname, "..", "model");
const M = JSON.parse(fs.readFileSync(path.join(MODEL_DIR, "model.json"), "utf-8"));

const LAKH = 100_000;
const BHK = { "1BHK": 1, "2BHK": 2, "3BHK": 3, "4BHK+": 4 };

// walk one tree to its leaf (iterative; LightGBM uses x <= threshold -> left)
function walk(node, x) {
  while (node.f !== undefined) node = x[node.f] <= node.t ? node.l : node.r;
  return node.v;
}
function rawScore(x) {
  let s = 0;
  for (const t of M.trees) s += walk(t, x);
  return s;
}
// piecewise-linear isotonic calibration, clamped at the ends
function calibrate(r) {
  const { x, y } = M.calibration;
  if (r <= x[0]) return y[0];
  if (r >= x[x.length - 1]) return y[y.length - 1];
  let lo = 0, hi = x.length - 1;
  while (hi - lo > 1) { const m = (lo + hi) >> 1; x[m] <= r ? (lo = m) : (hi = m); }
  const t = (r - x[lo]) / (x[hi] - x[lo]);
  return y[lo] + t * (y[hi] - y[lo]);
}
// 1 if the flat's price sits in the budget band the buyer is aiming at
function budgetMatch(budget, price) {
  for (const [lo, hi] of M.budget_bands_inr) {
    if (budget >= lo && budget <= hi) return price >= lo && price <= hi ? 1 : 0;
  }
  const top = M.budget_bands_inr[M.budget_bands_inr.length - 1];
  return price >= top[0] ? 1 : 0;
}

// raw form input -> the model's feature object (same recipe as preprocessing.py)
function buildFeatures(input) {
  const income = Number(input.income_l) * LAKH;
  const budget = Number(input.budget_l) * LAKH;
  const price = Number(input.price_l) * LAKH;
  if (!(income > 0) || !(budget > 0) || !(price > 0))
    throw new Error("income, budget and price must be positive numbers");
  if (!(input.bhk_pref in BHK) || !(input.bhk_enq in BHK))
    throw new Error("bhk_pref / bhk_enq must be one of 1BHK, 2BHK, 3BHK, 4BHK+");
  return {
    affordability_ratio: price / income,
    annual_income: income,
    price_to_budget: price / budget,
    budget_match: budgetMatch(budget, price),
    bhk_match: BHK[input.bhk_pref] === BHK[input.bhk_enq] ? 1 : 0,
    intent: input.intent === "investment" ? 1 : 0,
  };
}

export function scoreLead(input) {
  if (!input || typeof input !== "object") throw new Error("missing JSON body");
  const f = buildFeatures(input);
  const x = M.features.map((k) => f[k]);
  const p = Math.max(0, Math.min(1, calibrate(rawScore(x))));
  const base = M.base_rate;
  const priority = p >= 3 * base ? "HIGH" : p >= base ? "MEDIUM" : "LOW";
  return { p_buy: p, multiple: p / base, priority, base_rate: base, features: f };
}

export default function handler(req, res) {
  if (req.method !== "POST") {
    res.status(405).json({ error: "Use POST" });
    return;
  }
  try {
    const body = typeof req.body === "string" ? JSON.parse(req.body || "{}") : req.body;
    res.status(200).json(scoreLead(body));
  } catch (e) {
    res.status(400).json({ error: String(e.message || e) });
  }
}

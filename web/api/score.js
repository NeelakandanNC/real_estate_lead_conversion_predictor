// Vercel serverless function: scores one lead with the exported ONNX model.
// We load the model + meta once (reused across warm invocations), derive the same
// 6 features the model was trained on, run onnxruntime for the raw probability, then
// apply the isotonic calibration curve from meta.json. No Python in production.

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import * as ort from "onnxruntime-node";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const MODEL_DIR = fs.existsSync(path.join(process.cwd(), "model"))
  ? path.join(process.cwd(), "model")
  : path.join(__dirname, "..", "model");

const meta = JSON.parse(fs.readFileSync(path.join(MODEL_DIR, "meta.json"), "utf-8"));
const sessionPromise = ort.InferenceSession.create(
  path.join(MODEL_DIR, "lead_scorer.onnx")
);

const LAKH = 100_000;
const BHK = { "1BHK": 1, "2BHK": 2, "3BHK": 3, "4BHK+": 4 };

// 1 if the flat's price sits inside the budget band the buyer is aiming at
function budgetMatch(budget, price) {
  for (const [lo, hi] of meta.budget_bands_inr) {
    if (budget >= lo && budget <= hi) return price >= lo && price <= hi ? 1 : 0;
  }
  const top = meta.budget_bands_inr[meta.budget_bands_inr.length - 1];
  return price >= top[0] ? 1 : 0;
}

// piecewise-linear isotonic calibration (clamped at the ends)
function calibrate(p) {
  const { x, y } = meta.calibration_isotonic;
  if (p <= x[0]) return y[0];
  if (p >= x[x.length - 1]) return y[y.length - 1];
  let lo = 0, hi = x.length - 1;
  while (hi - lo > 1) { const m = (lo + hi) >> 1; x[m] <= p ? (lo = m) : (hi = m); }
  const t = (p - x[lo]) / (x[hi] - x[lo]);
  return y[lo] + t * (y[hi] - y[lo]);
}

// raw form input -> the model's feature vector (same recipe as preprocessing.py)
function buildFeatures(input) {
  const income = Number(input.income_l) * LAKH;
  const budget = Number(input.budget_l) * LAKH;
  const price = Number(input.price_l) * LAKH;
  const f = {
    affordability_ratio: price / income,
    annual_income: income,
    price_to_budget: price / budget,
    budget_match: budgetMatch(budget, price),
    bhk_match: BHK[input.bhk_pref] === BHK[input.bhk_enq] ? 1 : 0,
    intent: input.intent === "investment" ? 1 : 0,
  };
  return f;
}

export async function scoreLead(input) {
  const f = buildFeatures(input);
  const vec = Float32Array.from(meta.features.map((k) => f[k]));
  const session = await sessionPromise;
  const out = await session.run({
    input: new ort.Tensor("float32", vec, [1, meta.features.length]),
  });
  const probName = session.outputNames.find((n) => /prob/i.test(n)) ||
    session.outputNames[1];
  const raw = out[probName].data[1];           // P(class = buyer)
  const p = calibrate(raw);

  const base = meta.base_rate;
  const priority = p >= 3 * base ? "HIGH" : p >= base ? "MEDIUM" : "LOW";
  return { p_buy: p, multiple: p / base, priority, base_rate: base, features: f };
}

export default async function handler(req, res) {
  if (req.method !== "POST") {
    res.status(405).json({ error: "Use POST" });
    return;
  }
  try {
    const body = typeof req.body === "string" ? JSON.parse(req.body) : req.body;
    res.status(200).json(await scoreLead(body));
  } catch (e) {
    res.status(400).json({ error: String(e.message || e) });
  }
}

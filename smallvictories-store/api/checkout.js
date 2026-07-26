// Optional serverless checkout (deploy the store/ folder to Vercel).
// The static storefront works with Payment Links alone; use this only if you
// want programmatic Checkout Sessions (e.g. for a future cart).
//
// Env vars required on Vercel:
//   STRIPE_SECRET_KEY   — sk_test_... or sk_live_...
//   ALLOWED_ORIGIN      — e.g. https://smallvictories.com.au (for CORS)

import Stripe from "stripe";
import fs from "node:fs";
import path from "node:path";

const configDir = path.join(process.cwd(), "config");
const readJson = (f) => JSON.parse(fs.readFileSync(path.join(configDir, f), "utf8"));

export default async function handler(req, res) {
  const origin = process.env.ALLOWED_ORIGIN || "*";
  res.setHeader("Access-Control-Allow-Origin", origin);
  res.setHeader("Access-Control-Allow-Methods", "POST, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");
  if (req.method === "OPTIONS") return res.status(204).end();
  if (req.method !== "POST") return res.status(405).json({ error: "POST only" });

  try {
    const { priceId, colour, quantity = 1 } = req.body ?? {};
    const stripeConfig = readJson("stripe.json");
    const storeConfig = readJson("store.config.json");
    const frames = readJson("frames.json");

    // Only allow price IDs this store actually generated.
    const known = new Set(
      Object.values(stripeConfig.products).flatMap((p) =>
        Object.values(p.sizes).map((s) => s.priceId)
      )
    );
    if (!known.has(priceId)) return res.status(400).json({ error: "Unknown price" });
    if (!frames.colours.some((c) => c.id === colour))
      return res.status(400).json({ error: "Unknown frame colour" });

    const qty = Math.min(Math.max(parseInt(quantity, 10) || 1, 1), 10);
    const stripe = new Stripe(process.env.STRIPE_SECRET_KEY);
    const session = await stripe.checkout.sessions.create({
      mode: "payment",
      line_items: [{ price: priceId, quantity: qty }],
      shipping_address_collection: { allowed_countries: ["AU"] },
      phone_number_collection: { enabled: true },
      metadata: { frame_colour: colour },
      success_url: storeConfig.successUrl,
      cancel_url: storeConfig.cancelUrl,
    });
    return res.status(200).json({ url: session.url });
  } catch (err) {
    console.error(err);
    return res.status(500).json({ error: "Checkout failed" });
  }
}

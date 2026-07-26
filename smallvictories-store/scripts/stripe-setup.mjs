#!/usr/bin/env node
// Creates/updates Stripe Products, Prices and Payment Links from the store config,
// then writes the resulting IDs to store/config/stripe.json (used by the storefront).
//
// Usage:
//   cd store && npm install
//   STRIPE_SECRET_KEY=sk_test_... npm run stripe:setup          # test mode
//   STRIPE_SECRET_KEY=sk_live_... npm run stripe:setup -- --live # live mode (explicit opt-in)
//   npm run stripe:setup -- --dry-run                            # print the price table, no API calls
//
// Safe to re-run: products are matched by metadata, prices are replaced only when
// the amount changes (old prices are deactivated, never deleted).

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { retailPriceAud } from "../lib/pricing.mjs";

const storeDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const readJson = (p) => JSON.parse(fs.readFileSync(path.join(storeDir, p), "utf8"));

const config = readJson("config/store.config.json");
const frames = readJson("config/frames.json");
const prints = readJson("config/prints.json");

const args = process.argv.slice(2);
const DRY_RUN = args.includes("--dry-run");
const ALLOW_LIVE = args.includes("--live");

const sizesById = Object.fromEntries(frames.sizes.map((s) => [s.id, s]));

function priceTable() {
  const rows = [];
  for (const size of frames.sizes) {
    rows.push({
      size: size.label,
      "supplier cost (AUD)": size.costFramedAud + (size.estimate ? " (ESTIMATE)" : ""),
      "retail (AUD)": retailPriceAud(size.costFramedAud, config),
    });
  }
  return rows;
}

console.log(`\n${config.storeName}`);
console.log(`Markup: ${config.markup}×, rounded up to $${config.roundUpTo}\n`);
console.table(priceTable());

if (frames.costsAreEstimates) {
  console.warn(
    "⚠ frames.json costs are ESTIMATES. Replace them with real prices from\n" +
      `  ${frames.supplierUrl} before going live.\n`
  );
}

if (DRY_RUN) {
  console.log("Dry run — no Stripe calls made.");
  process.exit(0);
}

const key = process.env.STRIPE_SECRET_KEY;
if (!key) {
  console.error("Set STRIPE_SECRET_KEY (sk_test_... to start). Get it from https://dashboard.stripe.com/apikeys");
  process.exit(1);
}
if (key.startsWith("sk_live") && !ALLOW_LIVE) {
  console.error("Refusing to run with a LIVE key without the --live flag.");
  process.exit(1);
}

const { default: Stripe } = await import("stripe");
const stripe = new Stripe(key);

// Load previous run's output so re-runs update rather than duplicate.
const stripeJsonPath = path.join(storeDir, "config/stripe.json");
const existing = fs.existsSync(stripeJsonPath) ? JSON.parse(fs.readFileSync(stripeJsonPath, "utf8")) : {};
const out = { mode: key.startsWith("sk_live") ? "live" : "test", generatedBy: "stripe-setup.mjs", products: {} };

if (existing.mode && existing.mode !== out.mode) {
  console.warn(`⚠ Existing stripe.json is for ${existing.mode} mode; starting fresh for ${out.mode} mode.`);
  existing.products = {};
}

async function findProductBySlug(slug) {
  const res = await stripe.products.search({ query: `metadata['sv_slug']:'${slug}'`, limit: 1 });
  return res.data[0] ?? null;
}

const colourOptions = frames.colours.map((c) => ({ label: c.label, value: c.id }));

for (const print of prints.filter((p) => p.active)) {
  const name = `${print.title} — Framed Print`;
  let product = existing.products?.[print.slug]?.productId
    ? await stripe.products.retrieve(existing.products[print.slug].productId).catch(() => null)
    : await findProductBySlug(print.slug);

  if (!product) {
    product = await stripe.products.create({
      name,
      description: `${frames.notes}`,
      metadata: { sv_slug: print.slug, supplier: frames.supplier },
    });
    console.log(`+ product ${product.id}  ${name}`);
  } else if (product.name !== name) {
    product = await stripe.products.update(product.id, { name });
  }

  const entry = { productId: product.id, sizes: {} };

  for (const sizeId of print.sizes) {
    const size = sizesById[sizeId];
    if (!size) {
      console.warn(`⚠ ${print.slug}: unknown size '${sizeId}' — skipping`);
      continue;
    }
    const unitAmount = Math.round(retailPriceAud(size.costFramedAud, config) * 100);
    const prev = existing.products?.[print.slug]?.sizes?.[sizeId];

    let priceId = prev?.priceId ?? null;
    if (priceId) {
      const prevPrice = await stripe.prices.retrieve(priceId).catch(() => null);
      if (!prevPrice || prevPrice.unit_amount !== unitAmount || !prevPrice.active) {
        if (prevPrice?.active) await stripe.prices.update(priceId, { active: false });
        priceId = null;
      }
    }
    if (!priceId) {
      const price = await stripe.prices.create({
        product: product.id,
        currency: config.currency,
        unit_amount: unitAmount,
        nickname: `${size.label} framed`,
        metadata: { sv_size: sizeId },
      });
      priceId = price.id;
      console.log(`  + price ${priceId}  ${size.label}  $${unitAmount / 100} AUD`);
    }

    // Payment Link per print+size; frame colour is a dropdown at checkout.
    // Links are recreated whenever the price changed (links can't swap prices).
    let paymentLink = prev?.priceId === priceId ? prev?.paymentLink ?? null : null;
    if (!paymentLink) {
      const link = await stripe.paymentLinks.create({
        line_items: [
          {
            price: priceId,
            quantity: 1,
            adjustable_quantity: { enabled: true, minimum: 1, maximum: 10 },
          },
        ],
        shipping_address_collection: { allowed_countries: ["AU"] },
        phone_number_collection: { enabled: true },
        custom_fields: [
          {
            key: "frame_colour",
            label: { type: "custom", custom: "Frame colour" },
            type: "dropdown",
            dropdown: { options: colourOptions },
          },
        ],
        metadata: { sv_slug: print.slug, sv_size: sizeId },
        after_completion: { type: "redirect", redirect: { url: config.successUrl } },
      });
      paymentLink = link.url;
      console.log(`  + payment link  ${size.label}  ${paymentLink}`);
    }

    entry.sizes[sizeId] = { priceId, paymentLink };
  }

  out.products[print.slug] = entry;
}

fs.writeFileSync(stripeJsonPath, JSON.stringify(out, null, 2) + "\n");
console.log(`\nWrote ${path.relative(process.cwd(), stripeJsonPath)} (${out.mode} mode).`);
console.log("Commit it so the storefront picks up the payment links.");

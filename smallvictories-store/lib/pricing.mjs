// Shared pricing logic — used by the storefront (browser) and stripe-setup script (node).
// Retail price = supplier cost × markup, rounded UP to the nearest `roundUpTo` dollars.

export function retailPriceAud(costAud, { markup = 2, roundUpTo = 5 } = {}) {
  if (!(costAud > 0)) throw new Error(`Invalid supplier cost: ${costAud}`);
  const raw = costAud * markup;
  const step = roundUpTo > 0 ? roundUpTo : 1;
  return Math.ceil(raw / step) * step;
}

export function formatAud(amount) {
  return new Intl.NumberFormat("en-AU", {
    style: "currency",
    currency: "AUD",
    minimumFractionDigits: 0,
  }).format(amount);
}

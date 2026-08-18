const ALPACA_PAPER_BASE = "https://paper-api.alpaca.markets";

function finiteNumber(value, field) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) {
    throw new Error(`alpaca_${field}_missing_or_invalid`);
  }
  return parsed;
}

function requiredCredential(primary, legacy, field) {
  const value = String(process.env[primary] ?? process.env[legacy] ?? "").trim();
  if (!value) throw new Error(`${field}_missing`);
  return value;
}

export function requirePaperExecutionMode(value) {
  const mode = String(value ?? "").trim().toLowerCase();
  if (mode !== "paper") {
    throw new Error(`execution_mode_not_authorized:${mode || "missing"}`);
  }
  return ALPACA_PAPER_BASE;
}

export function requireFundedCapital(value) {
  const funded = Number(value);
  if (!Number.isFinite(funded) || funded <= 0) {
    throw new Error("vault_funded_amount_missing_or_invalid");
  }
  return funded;
}

export function calculateOpenBuyCommitment(orders) {
  if (!Array.isArray(orders)) throw new Error("alpaca_open_orders_invalid");

  return orders.reduce((total, order) => {
    if (!order || typeof order !== "object") throw new Error("alpaca_open_order_invalid");
    if (String(order.side ?? "").toLowerCase() !== "buy") return total;

    const qty = finiteNumber(order.qty, "open_order_qty");
    const filledQty = finiteNumber(order.filled_qty ?? 0, "open_order_filled_qty");
    const remainingQty = qty - filledQty;
    if (remainingQty <= 0) return total;

    const notional = Number(order.notional);
    if (Number.isFinite(notional) && notional > 0 && filledQty === 0) {
      return total + notional;
    }

    const price = Number(order.limit_price ?? order.stop_price);
    if (!Number.isFinite(price) || price <= 0) {
      throw new Error(`open_buy_commitment_unpriced:${String(order.symbol ?? "unknown")}`);
    }
    return total + remainingQty * price;
  }, 0);
}

export function normalizeEntryAccount(account, orders, funded) {
  if (!account || typeof account !== "object") throw new Error("alpaca_account_invalid");
  if (account.account_blocked === true || account.trading_blocked === true || account.trade_suspended_by_user === true) {
    throw new Error("alpaca_account_entry_blocked");
  }

  const cash = finiteNumber(account.cash, "cash");
  const buyingPower = finiteNumber(account.buying_power, "buying_power");
  const longMarketValue = finiteNumber(account.long_market_value, "long_market_value");
  const shortMarketValue = finiteNumber(account.short_market_value, "short_market_value");
  const openBuyCommitment = calculateOpenBuyCommitment(orders);
  const grossMarketExposure = Math.abs(longMarketValue) + Math.abs(shortMarketValue);

  return {
    cash: Math.max(0, Math.min(cash, buyingPower)),
    brokerCash: cash,
    buyingPower,
    grossMarketExposure,
    openBuyCommitment,
    invested: grossMarketExposure + openBuyCommitment,
    funded: requireFundedCapital(funded),
    openOrders: orders,
  };
}

async function alpacaJson(path, base, headers, fetchImpl) {
  const response = await fetchImpl(`${base}${path}`, {
    headers,
    signal: AbortSignal.timeout(8_000),
  });
  const text = await response.text();
  let body;
  try {
    body = text ? JSON.parse(text) : null;
  } catch {
    throw new Error(`alpaca_invalid_json:${path}`);
  }
  if (!response.ok) {
    const message = body && typeof body === "object" ? String(body.message ?? body.code ?? "") : "";
    throw new Error(`alpaca_http_${response.status}:${message || path}`);
  }
  return body;
}

export async function fetchPaperEntryCustody({ executionMode, fundedCapital, fetchImpl = fetch }) {
  const base = requirePaperExecutionMode(executionMode);
  const headers = {
    "APCA-API-KEY-ID": requiredCredential("APCA_API_KEY_ID", "ALPACA_API_KEY", "alpaca_api_key"),
    "APCA-API-SECRET-KEY": requiredCredential("APCA_API_SECRET_KEY", "ALPACA_SECRET_KEY", "alpaca_api_secret"),
  };

  const [account, orders] = await Promise.all([
    alpacaJson("/v2/account", base, headers, fetchImpl),
    alpacaJson("/v2/orders?status=open&limit=500", base, headers, fetchImpl),
  ]);
  return normalizeEntryAccount(account, orders, fundedCapital);
}

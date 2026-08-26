import "server-only";


export type ExecutionMode = "paper" | "live";

export type LedgerOpenPosition = {
  id: number;
  ticker: string;
  signal_class: string | null;
  shares: number;
  entry_filled_price: string | null;
  dollar_allocation: string | null;
  atr_14: string | null;
  spy_dk: number | null;
  s_uf: string | null;
  bar_count: number | null;
  status: string;
  signal_detected_at: string;
  entry_filled_at: string | null;
  alpaca_order_id: string | null;
};

export type AlpacaAccount = {
  equity: number | null;
  cash: number | null;
  portfolioValue: number | null;
  longMarketValue: number | null;
  shortMarketValue: number | null;
  lastEquity: number | null;
};

export type AlpacaPosition = {
  symbol: string;
  side: string;
  quantity: number;
  averageEntryPrice: number | null;
  currentPrice: number | null;
  marketValue: number | null;
  unrealizedPnl: number | null;
  unrealizedPnlPct: number | null;
};

export type AlpacaOpenOrder = {
  id: string;
  symbol: string;
  side: string;
  quantity: number | null;
  filledQuantity: number | null;
  status: string;
};

export type AlpacaCustodySnapshot = {
  status: "available" | "partial" | "unavailable";
  accountStatus: "available" | "unavailable";
  positionsStatus: "available" | "unavailable";
  ordersStatus: "available" | "unavailable";
  reasons: string[];
  fetchedAt: string;
  account: AlpacaAccount | null;
  positions: AlpacaPosition[] | null;
  openOrders: AlpacaOpenOrder[] | null;
};

// Delisted remnants frozen at the broker (verified inactive and
// not-tradable 2026-08-26; CWAN carries a pending merger announcement).
// Visible and labeled, excluded from the discrepancy count — no order
// of any kind is accepted on them; the broker clears them when it
// processes the corporate action.
const FROZEN_CORPORATE_ACTION_SYMBOLS = new Set(["CWAN", "HTBK"]);

export type CustodyStatus =
  | "matched"
  | "broker_only"
  | "frozen_corporate_action"
  | "ledger_only"
  | "quantity_mismatch"
  | "duplicate_ledger"
  | "pending_order"
  | "submitted_without_broker_order"
  | "broker_unavailable";

export type CustodyPosition = {
  id: string;
  ledger_ids: number[];
  ticker: string;
  signal_class: string;
  shares: number;
  ledger_shares: number;
  broker_shares: number | null;
  entry_price: number | null;
  current_price: number | null;
  market_value: number | null;
  dollar_allocation: number | null;
  unrealized_pl: number | null;
  unrealized_pl_pct: number | null;
  status: CustodyStatus;
  custody_status: CustodyStatus;
  custody_note: string;
  spy_dk: number | null;
  s_uf: number | null;
  bar_count: number | null;
  signal_detected_at: string;
  entry_filled_at: string | null;
  alpaca_order_id: string | null;
};

export type CustodySummary = {
  brokerPositions: number | null;
  ledgerSymbols: number;
  matched: number;
  discrepancies: number;
  unknownBecauseBrokerUnavailable: number;
  byStatus: Record<CustodyStatus, number>;
};


type RawRecord = Record<string, unknown>;


function finiteOrNull(value: unknown): number | null {
  if (value === null || value === undefined || value === "") return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}


function normalizedSymbol(value: unknown): string {
  return String(value ?? "").trim().toUpperCase();
}


function credentials(): { key: string; secret: string } | null {
  const key = process.env.APCA_API_KEY_ID ?? process.env.ALPACA_API_KEY ?? "";
  const secret = process.env.APCA_API_SECRET_KEY ?? process.env.ALPACA_SECRET_KEY ?? "";
  return key && secret ? { key, secret } : null;
}


function baseUrl(mode: ExecutionMode): string {
  if (mode !== "paper") throw new Error(`execution_mode_not_authorized:${mode}`);
  return "https://paper-api.alpaca.markets";
}


async function alpacaJson(url: string, auth: { key: string; secret: string }): Promise<unknown> {
  const response = await fetch(url, {
    headers: {
      "APCA-API-KEY-ID": auth.key,
      "APCA-API-SECRET-KEY": auth.secret,
    },
    cache: "no-store",
    signal: AbortSignal.timeout(8_000),
  });
  if (!response.ok) {
    throw new Error(`HTTP_${response.status}`);
  }
  return response.json();
}


function accountFrom(raw: unknown): AlpacaAccount {
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) throw new Error("INVALID_ACCOUNT_PAYLOAD");
  const value = raw as RawRecord;
  const account = {
    equity: finiteOrNull(value.equity),
    cash: finiteOrNull(value.cash),
    portfolioValue: finiteOrNull(value.portfolio_value),
    longMarketValue: finiteOrNull(value.long_market_value),
    shortMarketValue: finiteOrNull(value.short_market_value),
    lastEquity: finiteOrNull(value.last_equity),
  };
  if ((account.equity === null && account.portfolioValue === null) || account.cash === null) {
    throw new Error("INVALID_ACCOUNT_FIELDS");
  }
  return account;
}


function positionsFrom(raw: unknown): AlpacaPosition[] {
  if (!Array.isArray(raw)) throw new Error("INVALID_POSITIONS_PAYLOAD");
  return raw.map((item) => {
    const value = item && typeof item === "object" && !Array.isArray(item) ? item as RawRecord : {};
    const symbol = normalizedSymbol(value.symbol);
    const quantity = finiteOrNull(value.qty);
    if (!symbol || quantity === null) throw new Error("INVALID_POSITION_ROW");
    return {
      symbol,
      side: String(value.side ?? "unknown"),
      quantity,
      averageEntryPrice: finiteOrNull(value.avg_entry_price),
      currentPrice: finiteOrNull(value.current_price),
      marketValue: finiteOrNull(value.market_value),
      unrealizedPnl: finiteOrNull(value.unrealized_pl),
      unrealizedPnlPct: finiteOrNull(value.unrealized_plpc),
    };
  });
}


function ordersFrom(raw: unknown): AlpacaOpenOrder[] {
  if (!Array.isArray(raw)) throw new Error("INVALID_ORDERS_PAYLOAD");
  return raw.map((item) => {
    if (!item || typeof item !== "object" || Array.isArray(item)) throw new Error("INVALID_ORDER_ROW");
    const value = item as RawRecord;
    const order = {
      id: String(value.id ?? ""),
      symbol: normalizedSymbol(value.symbol),
      side: String(value.side ?? "unknown"),
      quantity: finiteOrNull(value.qty),
      filledQuantity: finiteOrNull(value.filled_qty),
      status: String(value.status ?? "unknown"),
    };
    if (!order.id || !order.symbol || order.quantity === null || order.filledQuantity === null) {
      throw new Error("INVALID_ORDER_FIELDS");
    }
    return order;
  });
}


function failureReason(label: string, result: PromiseSettledResult<unknown>): string | null {
  if (result.status === "fulfilled") return null;
  const message = result.reason instanceof Error ? result.reason.message : "UNKNOWN_ERROR";
  return `${label}:${message}`;
}


export async function fetchAlpacaCustody(mode: ExecutionMode): Promise<AlpacaCustodySnapshot> {
  const fetchedAt = new Date().toISOString();
  const auth = credentials();
  if (!auth) {
    return {
      status: "unavailable",
      accountStatus: "unavailable",
      positionsStatus: "unavailable",
      ordersStatus: "unavailable",
      reasons: ["credentials_missing"],
      fetchedAt,
      account: null,
      positions: null,
      openOrders: null,
    };
  }

  const base = baseUrl(mode);
  const [accountResult, positionsResult, ordersResult] = await Promise.allSettled([
    alpacaJson(`${base}/v2/account`, auth),
    alpacaJson(`${base}/v2/positions`, auth),
    alpacaJson(`${base}/v2/orders?status=open&limit=500&direction=desc`, auth),
  ]);
  const reasons = [
    failureReason("account", accountResult),
    failureReason("positions", positionsResult),
    failureReason("orders", ordersResult),
  ].filter((reason): reason is string => Boolean(reason));

  let account: AlpacaAccount | null = null;
  let positions: AlpacaPosition[] | null = null;
  let openOrders: AlpacaOpenOrder[] | null = null;
  try {
    if (accountResult.status === "fulfilled") account = accountFrom(accountResult.value);
  } catch (error) {
    reasons.push(`account:${error instanceof Error ? error.message : "INVALID_PAYLOAD"}`);
  }
  try {
    if (positionsResult.status === "fulfilled") positions = positionsFrom(positionsResult.value);
  } catch (error) {
    reasons.push(`positions:${error instanceof Error ? error.message : "INVALID_PAYLOAD"}`);
  }
  try {
    if (ordersResult.status === "fulfilled") openOrders = ordersFrom(ordersResult.value);
  } catch (error) {
    reasons.push(`orders:${error instanceof Error ? error.message : "INVALID_PAYLOAD"}`);
  }

  const availableCount = [account, positions, openOrders].filter((value) => value !== null).length;
  return {
    status: availableCount === 3 ? "available" : (availableCount === 0 ? "unavailable" : "partial"),
    accountStatus: account ? "available" : "unavailable",
    positionsStatus: positions ? "available" : "unavailable",
    ordersStatus: openOrders ? "available" : "unavailable",
    reasons: [...new Set(reasons)],
    fetchedAt,
    account,
    positions,
    openOrders,
  };
}


function weightedLedgerEntry(rows: LedgerOpenPosition[]): number | null {
  let quantity = 0;
  let cost = 0;
  for (const row of rows) {
    const entry = finiteOrNull(row.entry_filled_price);
    const shares = finiteOrNull(row.shares);
    if (entry === null || shares === null || shares <= 0) continue;
    quantity += shares;
    cost += entry * shares;
  }
  return quantity > 0 ? cost / quantity : null;
}


function nullableSum(values: Array<number | null>): number | null {
  const present = values.filter((value): value is number => value !== null);
  return present.length ? present.reduce((sum, value) => sum + value, 0) : null;
}


function newest(rows: LedgerOpenPosition[]): LedgerOpenPosition {
  return [...rows].sort((left, right) => right.signal_detected_at.localeCompare(left.signal_detected_at))[0];
}


function custodyNote(status: CustodyStatus, ledgerShares: number, brokerShares: number | null): string {
  if (status === "matched") return "Broker position and open-ledger quantity agree.";
  if (status === "broker_only") return "Alpaca holds this position, but no open ledger row owns it.";
  if (status === "frozen_corporate_action") return "Delisted asset frozen at the broker pending corporate-action settlement; no order of any kind is accepted. Leaves the account when the broker processes the action.";
  if (status === "ledger_only") return "Ledger says filled, but Alpaca has no corresponding position.";
  if (status === "quantity_mismatch") return `Quantity differs: ledger ${ledgerShares}, broker ${brokerShares}.`;
  if (status === "duplicate_ledger") return "More than one open ledger row claims this broker symbol.";
  if (status === "pending_order") return "Ledger submission has a matching open Alpaca order but no position fill yet.";
  if (status === "submitted_without_broker_order") return "Ledger says submitted, but Alpaca has neither a position nor an open order.";
  return "Broker position feed is unavailable, so custody cannot be reconciled.";
}


export function reconcileCustody(
  ledgerRows: LedgerOpenPosition[],
  brokerPositions: AlpacaPosition[] | null,
  openOrders: AlpacaOpenOrder[] | null,
): { positions: CustodyPosition[]; summary: CustodySummary } {
  const ledgerBySymbol = new Map<string, LedgerOpenPosition[]>();
  for (const row of ledgerRows) {
    const symbol = normalizedSymbol(row.ticker);
    if (!symbol) continue;
    ledgerBySymbol.set(symbol, [...(ledgerBySymbol.get(symbol) ?? []), row]);
  }
  const brokerBySymbol = brokerPositions === null
    ? null
    : new Map(brokerPositions.map((position) => [position.symbol, position]));
  const orderSymbols = openOrders === null ? null : new Set(openOrders.map((order) => order.symbol));
  const symbols = new Set(ledgerBySymbol.keys());
  if (brokerBySymbol) for (const symbol of brokerBySymbol.keys()) symbols.add(symbol);

  const positions: CustodyPosition[] = [];
  for (const symbol of [...symbols].sort()) {
    const rows = ledgerBySymbol.get(symbol) ?? [];
    const broker = brokerBySymbol?.get(symbol) ?? null;
    const ledgerShares = rows.reduce((sum, row) => sum + (finiteOrNull(row.shares) ?? 0), 0);
    let status: CustodyStatus;
    if (brokerBySymbol === null) {
      status = "broker_unavailable";
    } else if (!rows.length && broker) {
      // Known delisted remnants (verified inactive/not-tradable at the
      // broker 2026-08-26; CWAN carries a pending merger announcement).
      // They are visible, labeled, and excluded from the discrepancy
      // count -- there is nothing any engine can do with them.
      status = FROZEN_CORPORATE_ACTION_SYMBOLS.has(symbol)
        ? "frozen_corporate_action"
        : "broker_only";
    } else if (rows.length > 1) {
      status = "duplicate_ledger";
    } else if (broker) {
      status = Math.abs(ledgerShares - Math.abs(broker.quantity)) <= 1e-6 ? "matched" : "quantity_mismatch";
    } else if (rows.some((row) => row.status === "filled" || row.entry_filled_price !== null)) {
      status = "ledger_only";
    } else if (orderSymbols?.has(symbol)) {
      status = "pending_order";
    } else {
      status = "submitted_without_broker_order";
    }

    const primary = rows.length ? newest(rows) : null;
    const classes = [...new Set(rows.map((row) => row.signal_class ?? "manual"))];
    const brokerShares = broker ? Math.abs(broker.quantity) : null;
    positions.push({
      id: rows.length ? `ledger:${rows.map((row) => row.id).sort((a, b) => a - b).join(",")}` : `broker:${symbol}`,
      ledger_ids: rows.map((row) => row.id).sort((a, b) => a - b),
      ticker: symbol,
      signal_class: rows.length ? classes.join("+") : "BROKER",
      shares: brokerShares ?? ledgerShares,
      ledger_shares: ledgerShares,
      broker_shares: brokerShares,
      entry_price: broker?.averageEntryPrice ?? weightedLedgerEntry(rows),
      current_price: broker?.currentPrice ?? null,
      market_value: broker?.marketValue ?? null,
      dollar_allocation: nullableSum(rows.map((row) => finiteOrNull(row.dollar_allocation))),
      unrealized_pl: broker?.unrealizedPnl ?? null,
      unrealized_pl_pct: broker?.unrealizedPnlPct === null || broker?.unrealizedPnlPct === undefined
        ? null
        : broker.unrealizedPnlPct * 100,
      status,
      custody_status: status,
      custody_note: custodyNote(status, ledgerShares, brokerShares),
      spy_dk: primary?.spy_dk ?? null,
      s_uf: finiteOrNull(primary?.s_uf),
      bar_count: primary?.bar_count ?? null,
      signal_detected_at: primary?.signal_detected_at ?? "",
      entry_filled_at: primary?.entry_filled_at ?? null,
      alpaca_order_id: primary?.alpaca_order_id ?? null,
    });
  }

  const statuses: CustodyStatus[] = [
    "matched",
    "broker_only",
    "frozen_corporate_action",
    "ledger_only",
    "quantity_mismatch",
    "duplicate_ledger",
    "pending_order",
    "submitted_without_broker_order",
    "broker_unavailable",
  ];
  const byStatus = Object.fromEntries(statuses.map((status) => [status, 0])) as Record<CustodyStatus, number>;
  for (const position of positions) byStatus[position.custody_status] += 1;
  const discrepancyStatuses = new Set<CustodyStatus>([
    "broker_only",
    "ledger_only",
    "quantity_mismatch",
    "duplicate_ledger",
    "submitted_without_broker_order",
  ]);
  return {
    positions,
    summary: {
      brokerPositions: brokerPositions?.length ?? null,
      ledgerSymbols: ledgerBySymbol.size,
      matched: byStatus.matched,
      discrepancies: positions.filter((position) => discrepancyStatuses.has(position.custody_status)).length,
      unknownBecauseBrokerUnavailable: byStatus.broker_unavailable,
      byStatus,
    },
  };
}

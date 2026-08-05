// Auto-generated from FINVIZ v=111 filter schema (ft=1..6).
// Generated UTC: 2026-02-28T02:19:46Z

export type ScreenerFilterGroup = "descriptive" | "fundamental" | "technical" | "news" | "etf" | "all";

export type ScreenerFilterOption = {
  value: string;
  label: string;
  eliteOnly: boolean;
};

export type ScreenerFilterField = {
  key: string;
  label: string;
  dataFilter: string;
  groups: ScreenerFilterGroup[];
  options: ScreenerFilterOption[];
};

export const SCREENER_FILTER_GROUPS: ScreenerFilterGroup[] = ["descriptive", "fundamental", "technical", "news", "etf", "all"];

export const SCREENER_FILTER_FIELDS: Record<string, ScreenerFilterField> = {
  ah_change: {
    key: "ah_change",
    label: "After-Hours Change",
    dataFilter: "ah_change",
    groups: [
      "technical",
      "all"
    ],
    options: [
      {
        value: "",
        label: "Any",
        eliteOnly: false
      },
      {
        value: "custom_subscription",
        label: "Custom (Elite only)",
        eliteOnly: true
      }
    ]
  },
  ah_close: {
    key: "ah_close",
    label: "After-Hours Close",
    dataFilter: "ah_close",
    groups: [
      "technical",
      "all"
    ],
    options: [
      {
        value: "",
        label: "Any",
        eliteOnly: false
      },
      {
        value: "custom_subscription",
        label: "Custom (Elite only)",
        eliteOnly: true
      }
    ]
  },
  analystRecom: {
    key: "analystRecom",
    label: "Analyst Recom.",
    dataFilter: "an_recom",
    groups: [
      "descriptive",
      "all"
    ],
    options: [
      {
        value: "",
        label: "Any",
        eliteOnly: false
      },
      {
        value: "buy",
        label: "Buy",
        eliteOnly: false
      },
      {
        value: "buybetter",
        label: "Buy or better",
        eliteOnly: false
      },
      {
        value: "hold",
        label: "Hold",
        eliteOnly: false
      },
      {
        value: "holdbetter",
        label: "Hold or better",
        eliteOnly: false
      },
      {
        value: "holdworse",
        label: "Hold or worse",
        eliteOnly: false
      },
      {
        value: "sell",
        label: "Sell",
        eliteOnly: false
      },
      {
        value: "sellworse",
        label: "Sell or worse",
        eliteOnly: false
      },
      {
        value: "strongbuy",
        label: "Strong Buy (1)",
        eliteOnly: false
      },
      {
        value: "strongsell",
        label: "Strong Sell (5)",
        eliteOnly: false
      },
      {
        value: "custom_subscription",
        label: "Custom (Elite only)",
        eliteOnly: true
      }
    ]
  },
  avgVolume: {
    key: "avgVolume",
    label: "Average Volume",
    dataFilter: "sh_avgvol",
    groups: [
      "descriptive",
      "all"
    ],
    options: [
      {
        value: "",
        label: "Any",
        eliteOnly: false
      },
      {
        value: "100to1000",
        label: "100K to 1M",
        eliteOnly: false
      },
      {
        value: "100to500",
        label: "100K to 500K",
        eliteOnly: false
      },
      {
        value: "500to10000",
        label: "500K to 10M",
        eliteOnly: false
      },
      {
        value: "500to1000",
        label: "500K to 1M",
        eliteOnly: false
      },
      {
        value: "o100",
        label: "Over 100K",
        eliteOnly: false
      },
      {
        value: "o1000",
        label: "Over 1M",
        eliteOnly: false
      },
      {
        value: "o200",
        label: "Over 200K",
        eliteOnly: false
      },
      {
        value: "o2000",
        label: "Over 2M",
        eliteOnly: false
      },
      {
        value: "o300",
        label: "Over 300K",
        eliteOnly: false
      },
      {
        value: "o400",
        label: "Over 400K",
        eliteOnly: false
      },
      {
        value: "o500",
        label: "Over 500K",
        eliteOnly: false
      },
      {
        value: "o50",
        label: "Over 50K",
        eliteOnly: false
      },
      {
        value: "o750",
        label: "Over 750K",
        eliteOnly: false
      },
      {
        value: "u100",
        label: "Under 100K",
        eliteOnly: false
      },
      {
        value: "u1000",
        label: "Under 1M",
        eliteOnly: false
      },
      {
        value: "u500",
        label: "Under 500K",
        eliteOnly: false
      },
      {
        value: "u50",
        label: "Under 50K",
        eliteOnly: false
      },
      {
        value: "u750",
        label: "Under 750K",
        eliteOnly: false
      },
      {
        value: "custom_subscription",
        label: "Custom (Elite only)",
        eliteOnly: true
      }
    ]
  },
  country: {
    key: "country",
    label: "Country",
    dataFilter: "geo",
    groups: [
      "descriptive",
      "all"
    ],
    options: [
      {
        value: "",
        label: "Any",
        eliteOnly: false
      },
      {
        value: "argentina",
        label: "Argentina",
        eliteOnly: false
      },
      {
        value: "asia",
        label: "Asia",
        eliteOnly: false
      },
      {
        value: "australia",
        label: "Australia",
        eliteOnly: false
      },
      {
        value: "bric",
        label: "BRIC",
        eliteOnly: false
      },
      {
        value: "bahamas",
        label: "Bahamas",
        eliteOnly: false
      },
      {
        value: "benelux",
        label: "BeNeLux",
        eliteOnly: false
      },
      {
        value: "belgium",
        label: "Belgium",
        eliteOnly: false
      },
      {
        value: "bermuda",
        label: "Bermuda",
        eliteOnly: false
      },
      {
        value: "brazil",
        label: "Brazil",
        eliteOnly: false
      },
      {
        value: "canada",
        label: "Canada",
        eliteOnly: false
      },
      {
        value: "caymanislands",
        label: "Cayman Islands",
        eliteOnly: false
      },
      {
        value: "chile",
        label: "Chile",
        eliteOnly: false
      },
      {
        value: "china",
        label: "China",
        eliteOnly: false
      },
      {
        value: "chinahongkong",
        label: "China & Hong Kong",
        eliteOnly: false
      },
      {
        value: "colombia",
        label: "Colombia",
        eliteOnly: false
      },
      {
        value: "cyprus",
        label: "Cyprus",
        eliteOnly: false
      },
      {
        value: "denmark",
        label: "Denmark",
        eliteOnly: false
      },
      {
        value: "europe",
        label: "Europe",
        eliteOnly: false
      },
      {
        value: "finland",
        label: "Finland",
        eliteOnly: false
      },
      {
        value: "notusa",
        label: "Foreign (ex-USA)",
        eliteOnly: false
      },
      {
        value: "france",
        label: "France",
        eliteOnly: false
      },
      {
        value: "germany",
        label: "Germany",
        eliteOnly: false
      },
      {
        value: "greece",
        label: "Greece",
        eliteOnly: false
      },
      {
        value: "hongkong",
        label: "Hong Kong",
        eliteOnly: false
      },
      {
        value: "hungary",
        label: "Hungary",
        eliteOnly: false
      },
      {
        value: "iceland",
        label: "Iceland",
        eliteOnly: false
      },
      {
        value: "india",
        label: "India",
        eliteOnly: false
      },
      {
        value: "indonesia",
        label: "Indonesia",
        eliteOnly: false
      },
      {
        value: "ireland",
        label: "Ireland",
        eliteOnly: false
      },
      {
        value: "israel",
        label: "Israel",
        eliteOnly: false
      },
      {
        value: "italy",
        label: "Italy",
        eliteOnly: false
      },
      {
        value: "japan",
        label: "Japan",
        eliteOnly: false
      },
      {
        value: "jordan",
        label: "Jordan",
        eliteOnly: false
      },
      {
        value: "kazakhstan",
        label: "Kazakhstan",
        eliteOnly: false
      },
      {
        value: "latinamerica",
        label: "Latin America",
        eliteOnly: false
      },
      {
        value: "luxembourg",
        label: "Luxembourg",
        eliteOnly: false
      },
      {
        value: "malaysia",
        label: "Malaysia",
        eliteOnly: false
      },
      {
        value: "malta",
        label: "Malta",
        eliteOnly: false
      },
      {
        value: "mexico",
        label: "Mexico",
        eliteOnly: false
      },
      {
        value: "monaco",
        label: "Monaco",
        eliteOnly: false
      },
      {
        value: "netherlands",
        label: "Netherlands",
        eliteOnly: false
      },
      {
        value: "newzealand",
        label: "New Zealand",
        eliteOnly: false
      },
      {
        value: "norway",
        label: "Norway",
        eliteOnly: false
      },
      {
        value: "panama",
        label: "Panama",
        eliteOnly: false
      },
      {
        value: "peru",
        label: "Peru",
        eliteOnly: false
      },
      {
        value: "philippines",
        label: "Philippines",
        eliteOnly: false
      },
      {
        value: "portugal",
        label: "Portugal",
        eliteOnly: false
      },
      {
        value: "russia",
        label: "Russia",
        eliteOnly: false
      },
      {
        value: "singapore",
        label: "Singapore",
        eliteOnly: false
      },
      {
        value: "southafrica",
        label: "South Africa",
        eliteOnly: false
      },
      {
        value: "southkorea",
        label: "South Korea",
        eliteOnly: false
      },
      {
        value: "spain",
        label: "Spain",
        eliteOnly: false
      },
      {
        value: "sweden",
        label: "Sweden",
        eliteOnly: false
      },
      {
        value: "switzerland",
        label: "Switzerland",
        eliteOnly: false
      },
      {
        value: "taiwan",
        label: "Taiwan",
        eliteOnly: false
      },
      {
        value: "thailand",
        label: "Thailand",
        eliteOnly: false
      },
      {
        value: "turkey",
        label: "Turkey",
        eliteOnly: false
      },
      {
        value: "usa",
        label: "USA",
        eliteOnly: false
      },
      {
        value: "unitedarabemirates",
        label: "United Arab Emirates",
        eliteOnly: false
      },
      {
        value: "unitedkingdom",
        label: "United Kingdom",
        eliteOnly: false
      },
      {
        value: "uruguay",
        label: "Uruguay",
        eliteOnly: false
      },
      {
        value: "vietnam",
        label: "Vietnam",
        eliteOnly: false
      },
      {
        value: "custom_subscription",
        label: "Custom (Elite only)",
        eliteOnly: true
      }
    ]
  },
  currentVolume: {
    key: "currentVolume",
    label: "Current Volume",
    dataFilter: "sh_curvol",
    groups: [
      "descriptive",
      "all"
    ],
    options: [
      {
        value: "",
        label: "Any",
        eliteOnly: false
      },
      {
        value: "ousd100000",
        label: "Over $100M",
        eliteOnly: false
      },
      {
        value: "ousd10000",
        label: "Over $10M",
        eliteOnly: false
      },
      {
        value: "ousd1000000",
        label: "Over $1B",
        eliteOnly: false
      },
      {
        value: "ousd1000",
        label: "Over $1M",
        eliteOnly: false
      },
      {
        value: "o0",
        label: "Over 0",
        eliteOnly: false
      },
      {
        value: "o100sf",
        label: "Over 100% shares float",
        eliteOnly: false
      },
      {
        value: "o100",
        label: "Over 100K",
        eliteOnly: false
      },
      {
        value: "o10000",
        label: "Over 10M",
        eliteOnly: false
      },
      {
        value: "o1000",
        label: "Over 1M",
        eliteOnly: false
      },
      {
        value: "o200",
        label: "Over 200K",
        eliteOnly: false
      },
      {
        value: "o20000",
        label: "Over 20M",
        eliteOnly: false
      },
      {
        value: "o2000",
        label: "Over 2M",
        eliteOnly: false
      },
      {
        value: "o300",
        label: "Over 300K",
        eliteOnly: false
      },
      {
        value: "o400",
        label: "Over 400K",
        eliteOnly: false
      },
      {
        value: "o50sf",
        label: "Over 50% shares float",
        eliteOnly: false
      },
      {
        value: "o500",
        label: "Over 500K",
        eliteOnly: false
      },
      {
        value: "o50",
        label: "Over 50K",
        eliteOnly: false
      },
      {
        value: "o5000",
        label: "Over 5M",
        eliteOnly: false
      },
      {
        value: "o750",
        label: "Over 750K",
        eliteOnly: false
      },
      {
        value: "uusd100000",
        label: "Under $100M",
        eliteOnly: false
      },
      {
        value: "uusd10000",
        label: "Under $10M",
        eliteOnly: false
      },
      {
        value: "uusd1000000",
        label: "Under $1B",
        eliteOnly: false
      },
      {
        value: "uusd1000",
        label: "Under $1M",
        eliteOnly: false
      },
      {
        value: "u100",
        label: "Under 100K",
        eliteOnly: false
      },
      {
        value: "u1000",
        label: "Under 1M",
        eliteOnly: false
      },
      {
        value: "u500",
        label: "Under 500K",
        eliteOnly: false
      },
      {
        value: "u50",
        label: "Under 50K",
        eliteOnly: false
      },
      {
        value: "u750",
        label: "Under 750K",
        eliteOnly: false
      },
      {
        value: "custom_subscription",
        label: "Custom (Elite only)",
        eliteOnly: true
      }
    ]
  },
  dividendYield: {
    key: "dividendYield",
    label: "Dividend Yield",
    dataFilter: "fa_div",
    groups: [
      "descriptive",
      "all"
    ],
    options: [
      {
        value: "",
        label: "Any",
        eliteOnly: false
      },
      {
        value: "high",
        label: "High (>5%)",
        eliteOnly: false
      },
      {
        value: "none",
        label: "None (0%)",
        eliteOnly: false
      },
      {
        value: "o1",
        label: "Over 1%",
        eliteOnly: false
      },
      {
        value: "o10",
        label: "Over 10%",
        eliteOnly: false
      },
      {
        value: "o2",
        label: "Over 2%",
        eliteOnly: false
      },
      {
        value: "o3",
        label: "Over 3%",
        eliteOnly: false
      },
      {
        value: "o4",
        label: "Over 4%",
        eliteOnly: false
      },
      {
        value: "o5",
        label: "Over 5%",
        eliteOnly: false
      },
      {
        value: "o6",
        label: "Over 6%",
        eliteOnly: false
      },
      {
        value: "o7",
        label: "Over 7%",
        eliteOnly: false
      },
      {
        value: "o8",
        label: "Over 8%",
        eliteOnly: false
      },
      {
        value: "o9",
        label: "Over 9%",
        eliteOnly: false
      },
      {
        value: "pos",
        label: "Positive (>0%)",
        eliteOnly: false
      },
      {
        value: "veryhigh",
        label: "Very High (>10%)",
        eliteOnly: false
      },
      {
        value: "custom_subscription",
        label: "Custom (Elite only)",
        eliteOnly: true
      }
    ]
  },
  earningsDate: {
    key: "earningsDate",
    label: "Earnings Date",
    dataFilter: "earningsdate",
    groups: [
      "descriptive",
      "all"
    ],
    options: [
      {
        value: "",
        label: "Any",
        eliteOnly: false
      },
      {
        value: "nextdays5",
        label: "Next 5 Days",
        eliteOnly: false
      },
      {
        value: "nextweek",
        label: "Next Week",
        eliteOnly: false
      },
      {
        value: "prevdays5",
        label: "Previous 5 Days",
        eliteOnly: false
      },
      {
        value: "prevweek",
        label: "Previous Week",
        eliteOnly: false
      },
      {
        value: "thismonth",
        label: "This Month",
        eliteOnly: false
      },
      {
        value: "thisweek",
        label: "This Week",
        eliteOnly: false
      },
      {
        value: "today",
        label: "Today",
        eliteOnly: false
      },
      {
        value: "todayafter",
        label: "Today After Market Close",
        eliteOnly: false
      },
      {
        value: "todaybefore",
        label: "Today Before Market Open",
        eliteOnly: false
      },
      {
        value: "tomorrow",
        label: "Tomorrow",
        eliteOnly: false
      },
      {
        value: "tomorrowafter",
        label: "Tomorrow After Market Close",
        eliteOnly: false
      },
      {
        value: "tomorrowbefore",
        label: "Tomorrow Before Market Open",
        eliteOnly: false
      },
      {
        value: "yesterday",
        label: "Yesterday",
        eliteOnly: false
      },
      {
        value: "yesterdayafter",
        label: "Yesterday After Market Close",
        eliteOnly: false
      },
      {
        value: "yesterdaybefore",
        label: "Yesterday Before Market Open",
        eliteOnly: false
      },
      {
        value: "custom_subscription",
        label: "Custom (Elite only)",
        eliteOnly: true
      }
    ]
  },
  etf_active: {
    key: "etf_active",
    label: "Active/Passive",
    dataFilter: "etf_active",
    groups: [
      "etf"
    ],
    options: [
      {
        value: "custom_subscription",
        label: "Elite only",
        eliteOnly: true
      }
    ]
  },
  etf_assettype: {
    key: "etf_assettype",
    label: "Asset Type",
    dataFilter: "etf_assettype",
    groups: [
      "all",
      "etf"
    ],
    options: [
      {
        value: "",
        label: "Any",
        eliteOnly: false
      },
      {
        value: "bonds",
        label: "Bonds",
        eliteOnly: false
      },
      {
        value: "carbontrading",
        label: "Carbon Trading",
        eliteOnly: false
      },
      {
        value: "closedendfunds",
        label: "Closed End Funds",
        eliteOnly: false
      },
      {
        value: "commoditiesmetals",
        label: "Commodities & Metals",
        eliteOnly: false
      },
      {
        value: "cryptocurrency",
        label: "CryptoCurrency",
        eliteOnly: false
      },
      {
        value: "currency",
        label: "Currency",
        eliteOnly: false
      },
      {
        value: "equitiesstocks",
        label: "Equities (Stocks)",
        eliteOnly: false
      },
      {
        value: "equitiesstocksipobased",
        label: "Equities (Stocks) - IPO Based",
        eliteOnly: false
      },
      {
        value: "freightfutures",
        label: "Freight Futures",
        eliteOnly: false
      },
      {
        value: "hedgefundreplication",
        label: "Hedge Fund Replication",
        eliteOnly: false
      },
      {
        value: "mlp",
        label: "MLP",
        eliteOnly: false
      },
      {
        value: "multiassetconservative",
        label: "Multi-Asset - Conservative",
        eliteOnly: false
      },
      {
        value: "multiassetgrowthaggressive",
        label: "Multi-Asset - Growth / Aggressive",
        eliteOnly: false
      },
      {
        value: "multiassetmoderate",
        label: "Multi-Asset - Moderate",
        eliteOnly: false
      },
      {
        value: "multiassetspreadbetweenassetclasses",
        label: "Multi-Asset - Spread Between Asset Classes",
        eliteOnly: false
      },
      {
        value: "multiassettacticalactive",
        label: "Multi-Asset - Tactical / Active",
        eliteOnly: false
      },
      {
        value: "multiassettargetdate2030",
        label: "Multi-AssetTarget Date - 2030",
        eliteOnly: false
      },
      {
        value: "multiassettargetdate2035",
        label: "Multi-AssetTarget Date - 2035",
        eliteOnly: false
      },
      {
        value: "multiassettargetdate2040",
        label: "Multi-AssetTarget Date - 2040",
        eliteOnly: false
      },
      {
        value: "multiassettargetdate2045",
        label: "Multi-AssetTarget Date - 2045",
        eliteOnly: false
      },
      {
        value: "multiassettargetdate2050",
        label: "Multi-AssetTarget Date - 2050",
        eliteOnly: false
      },
      {
        value: "multiassettargetdate2055",
        label: "Multi-AssetTarget Date - 2055",
        eliteOnly: false
      },
      {
        value: "multiassettargetdate2060",
        label: "Multi-AssetTarget Date - 2060",
        eliteOnly: false
      },
      {
        value: "multiassettargetdate2065",
        label: "Multi-AssetTarget Date - 2065",
        eliteOnly: false
      },
      {
        value: "multiassettargetdate2070",
        label: "Multi-AssetTarget Date - 2070",
        eliteOnly: false
      },
      {
        value: "preferredstock",
        label: "Preferred Stock",
        eliteOnly: false
      },
      {
        value: "privateequity",
        label: "Private Equity",
        eliteOnly: false
      },
      {
        value: "spac",
        label: "SPAC",
        eliteOnly: false
      },
      {
        value: "custom_subscription",
        label: "Custom (Elite only)",
        eliteOnly: true
      }
    ]
  },
  etf_bondmaturity: {
    key: "etf_bondmaturity",
    label: "Average Maturity",
    dataFilter: "etf_bondmaturity",
    groups: [
      "etf"
    ],
    options: [
      {
        value: "custom_subscription",
        label: "Elite only",
        eliteOnly: true
      }
    ]
  },
  etf_bondtype: {
    key: "etf_bondtype",
    label: "Bond Type",
    dataFilter: "etf_bondtype",
    groups: [
      "etf"
    ],
    options: [
      {
        value: "custom_subscription",
        label: "Elite only",
        eliteOnly: true
      }
    ]
  },
  etf_category: {
    key: "etf_category",
    label: "Single Category",
    dataFilter: "etf_category",
    groups: [
      "all",
      "etf"
    ],
    options: [
      {
        value: "",
        label: "Any",
        eliteOnly: false
      },
      {
        value: "bondsbroadmarket",
        label: "Bonds - Broad Market",
        eliteOnly: false
      },
      {
        value: "bondsconvertible",
        label: "Bonds - Convertible",
        eliteOnly: false
      },
      {
        value: "bondscorporate",
        label: "Bonds - Corporate",
        eliteOnly: false
      },
      {
        value: "bondsinflationprotected",
        label: "Bonds - Inflation protected",
        eliteOnly: false
      },
      {
        value: "bondsleveragedinverse",
        label: "Bonds - Leveraged / Inverse",
        eliteOnly: false
      },
      {
        value: "bondsmoneymarket",
        label: "Bonds - Money Market",
        eliteOnly: false
      },
      {
        value: "bondsmortgage",
        label: "Bonds - Mortgage",
        eliteOnly: false
      },
      {
        value: "bondsmunicipal",
        label: "Bonds - Municipal",
        eliteOnly: false
      },
      {
        value: "bondsnongovernmentassetbackedsecurities",
        label: "Bonds - Non Government Asset Backed Securities",
        eliteOnly: false
      },
      {
        value: "bondstreasurygovernment",
        label: "Bonds - Treasury & Government",
        eliteOnly: false
      },
      {
        value: "commoditiesmetalsagricultural",
        label: "Commodities & Metals - Agricultural",
        eliteOnly: false
      },
      {
        value: "commoditiesmetalsdiversifiedcommodities",
        label: "Commodities & Metals - Diversified Commodities",
        eliteOnly: false
      },
      {
        value: "commoditiesmetalsenergy",
        label: "Commodities & Metals - Energy",
        eliteOnly: false
      },
      {
        value: "commoditiesmetalsgoldmetals",
        label: "Commodities & Metals - Gold / Metals",
        eliteOnly: false
      },
      {
        value: "commoditiesmetalsleveragedinverse",
        label: "Commodities & Metals - Leveraged / Inverse",
        eliteOnly: false
      },
      {
        value: "currency",
        label: "Currency",
        eliteOnly: false
      },
      {
        value: "currencyleveragedinverse",
        label: "Currency - Leveraged / Inverse",
        eliteOnly: false
      },
      {
        value: "equityleveragedinverse",
        label: "Equity - Leveraged / Inverse",
        eliteOnly: false
      },
      {
        value: "globalorexusequitiesbroadregional",
        label: "Global or ExUS Equities - Broad / Regional",
        eliteOnly: false
      },
      {
        value: "globalorexusequitiescountryspecific",
        label: "Global or ExUS Equities - Country Specific",
        eliteOnly: false
      },
      {
        value: "globalorexusequitiesdividendfundamental",
        label: "Global or ExUS Equities - Dividend & Fundamental",
        eliteOnly: false
      },
      {
        value: "globalorexusequitiesfactorthematic",
        label: "Global or ExUS Equities - Factor & Thematic",
        eliteOnly: false
      },
      {
        value: "globalorexusequitiesindustrysector",
        label: "Global or ExUS Equities - Industry Sector",
        eliteOnly: false
      },
      {
        value: "globalorexusequitiesquantstrat",
        label: "Global or ExUS Equities - Quant Strat",
        eliteOnly: false
      },
      {
        value: "otherassettypesleveragedinverse",
        label: "Other Asset Types - Leveraged / Inverse",
        eliteOnly: false
      },
      {
        value: "otherassettypesmultiassetother",
        label: "Other Asset Types - Multi-Asset / Other",
        eliteOnly: false
      },
      {
        value: "targetdatemultiassetleveragedinverse",
        label: "Target Date / Multi-Asset - Leveraged / Inverse",
        eliteOnly: false
      },
      {
        value: "targetdatemultiassetother",
        label: "Target Date / Multi-Asset - Other",
        eliteOnly: false
      },
      {
        value: "usequitiesbroadmarketsize",
        label: "US Equities - Broad Market & Size",
        eliteOnly: false
      },
      {
        value: "usequitiesdividendfundamental",
        label: "US Equities - Dividend & Fundamental",
        eliteOnly: false
      },
      {
        value: "usequitiesfactorthematic",
        label: "US Equities - Factor & Thematic",
        eliteOnly: false
      },
      {
        value: "usequitiesindustrysector",
        label: "US Equities - Industry Sector",
        eliteOnly: false
      },
      {
        value: "usequitiesquantstrat",
        label: "US Equities - Quant Strat",
        eliteOnly: false
      },
      {
        value: "usequitiesusstyle",
        label: "US Equities - US Style",
        eliteOnly: false
      },
      {
        value: "custom_subscription",
        label: "Custom (Elite only)",
        eliteOnly: true
      }
    ]
  },
  etf_commoditytype: {
    key: "etf_commoditytype",
    label: "Commodity Type",
    dataFilter: "etf_commoditytype",
    groups: [
      "etf"
    ],
    options: [
      {
        value: "custom_subscription",
        label: "Elite only",
        eliteOnly: true
      }
    ]
  },
  etf_currency: {
    key: "etf_currency",
    label: "Currency",
    dataFilter: "etf_currency",
    groups: [
      "etf"
    ],
    options: [
      {
        value: "custom_subscription",
        label: "Elite only",
        eliteOnly: true
      }
    ]
  },
  etf_developed: {
    key: "etf_developed",
    label: "Developed/Emerging",
    dataFilter: "etf_developed",
    groups: [
      "etf"
    ],
    options: [
      {
        value: "custom_subscription",
        label: "Elite only",
        eliteOnly: true
      }
    ]
  },
  etf_dividendtype: {
    key: "etf_dividendtype",
    label: "Dividend Type",
    dataFilter: "etf_dividendtype",
    groups: [
      "etf"
    ],
    options: [
      {
        value: "custom_subscription",
        label: "Elite only",
        eliteOnly: true
      }
    ]
  },
  etf_esgtype: {
    key: "etf_esgtype",
    label: "ESG Type",
    dataFilter: "etf_esgtype",
    groups: [
      "etf"
    ],
    options: [
      {
        value: "custom_subscription",
        label: "Elite only",
        eliteOnly: true
      }
    ]
  },
  etf_etftype: {
    key: "etf_etftype",
    label: "ETF Type",
    dataFilter: "etf_etftype",
    groups: [
      "etf"
    ],
    options: [
      {
        value: "custom_subscription",
        label: "Elite only",
        eliteOnly: true
      }
    ]
  },
  etf_fundflows: {
    key: "etf_fundflows",
    label: "Net Fund Flows",
    dataFilter: "etf_fundflows",
    groups: [
      "all",
      "etf"
    ],
    options: [
      {
        value: "",
        label: "Any",
        eliteOnly: false
      },
      {
        value: "1mo0",
        label: "1 Month - Over 0%",
        eliteOnly: false
      },
      {
        value: "1mo10",
        label: "1 Month - Over 10%",
        eliteOnly: false
      },
      {
        value: "1mo25",
        label: "1 Month - Over 25%",
        eliteOnly: false
      },
      {
        value: "1mo50",
        label: "1 Month - Over 50%",
        eliteOnly: false
      },
      {
        value: "1mu10",
        label: "1 Month - Under -10%",
        eliteOnly: false
      },
      {
        value: "1mu25",
        label: "1 Month - Under -25%",
        eliteOnly: false
      },
      {
        value: "1mu50",
        label: "1 Month - Under -50%",
        eliteOnly: false
      },
      {
        value: "1mu0",
        label: "1 Month - Under 0%",
        eliteOnly: false
      },
      {
        value: "3mo0",
        label: "3 Month - Over 0%",
        eliteOnly: false
      },
      {
        value: "3mo10",
        label: "3 Month - Over 10%",
        eliteOnly: false
      },
      {
        value: "3mo25",
        label: "3 Month - Over 25%",
        eliteOnly: false
      },
      {
        value: "3mo50",
        label: "3 Month - Over 50%",
        eliteOnly: false
      },
      {
        value: "3mu10",
        label: "3 Month - Under -10%",
        eliteOnly: false
      },
      {
        value: "3mu25",
        label: "3 Month - Under -25%",
        eliteOnly: false
      },
      {
        value: "3mu50",
        label: "3 Month - Under -50%",
        eliteOnly: false
      },
      {
        value: "3mu0",
        label: "3 Month - Under 0%",
        eliteOnly: false
      },
      {
        value: "ytdo0",
        label: "YTD - Over 0%",
        eliteOnly: false
      },
      {
        value: "ytdo10",
        label: "YTD - Over 10%",
        eliteOnly: false
      },
      {
        value: "ytdo25",
        label: "YTD - Over 25%",
        eliteOnly: false
      },
      {
        value: "ytdo50",
        label: "YTD - Over 50%",
        eliteOnly: false
      },
      {
        value: "ytdu10",
        label: "YTD - Under -10%",
        eliteOnly: false
      },
      {
        value: "ytdu25",
        label: "YTD - Under -25%",
        eliteOnly: false
      },
      {
        value: "ytdu50",
        label: "YTD - Under -50%",
        eliteOnly: false
      },
      {
        value: "ytdu0",
        label: "YTD - Under 0%",
        eliteOnly: false
      },
      {
        value: "custom_subscription",
        label: "More (Elite only)",
        eliteOnly: true
      }
    ]
  },
  etf_growthvalue: {
    key: "etf_growthvalue",
    label: "Growth/Value",
    dataFilter: "etf_growthvalue",
    groups: [
      "etf"
    ],
    options: [
      {
        value: "custom_subscription",
        label: "Elite only",
        eliteOnly: true
      }
    ]
  },
  etf_indexweight: {
    key: "etf_indexweight",
    label: "Index Weighting",
    dataFilter: "etf_indexweight",
    groups: [
      "etf"
    ],
    options: [
      {
        value: "custom_subscription",
        label: "Elite only",
        eliteOnly: true
      }
    ]
  },
  etf_inverse: {
    key: "etf_inverse",
    label: "Inverse/Leveraged",
    dataFilter: "etf_inverse",
    groups: [
      "etf"
    ],
    options: [
      {
        value: "custom_subscription",
        label: "Elite only",
        eliteOnly: true
      }
    ]
  },
  etf_mktcap: {
    key: "etf_mktcap",
    label: "Market Cap. (ETF)",
    dataFilter: "etf_mktcap",
    groups: [
      "etf"
    ],
    options: [
      {
        value: "custom_subscription",
        label: "Elite only",
        eliteOnly: true
      }
    ]
  },
  etf_nav: {
    key: "etf_nav",
    label: "Net Asset Value%",
    dataFilter: "etf_nav",
    groups: [
      "etf"
    ],
    options: [
      {
        value: "custom_subscription",
        label: "Elite only",
        eliteOnly: true
      }
    ]
  },
  etf_netexpense: {
    key: "etf_netexpense",
    label: "Net Expense Ratio",
    dataFilter: "etf_netexpense",
    groups: [
      "all",
      "etf"
    ],
    options: [
      {
        value: "",
        label: "Any",
        eliteOnly: false
      },
      {
        value: "u01",
        label: "Under 0.1%",
        eliteOnly: false
      },
      {
        value: "u02",
        label: "Under 0.2%",
        eliteOnly: false
      },
      {
        value: "u03",
        label: "Under 0.3%",
        eliteOnly: false
      },
      {
        value: "u04",
        label: "Under 0.4%",
        eliteOnly: false
      },
      {
        value: "u05",
        label: "Under 0.5%",
        eliteOnly: false
      },
      {
        value: "u06",
        label: "Under 0.6%",
        eliteOnly: false
      },
      {
        value: "u07",
        label: "Under 0.7%",
        eliteOnly: false
      },
      {
        value: "u08",
        label: "Under 0.8%",
        eliteOnly: false
      },
      {
        value: "u09",
        label: "Under 0.9%",
        eliteOnly: false
      },
      {
        value: "u10",
        label: "Under 1.0%",
        eliteOnly: false
      },
      {
        value: "custom_subscription",
        label: "Custom (Elite only)",
        eliteOnly: true
      }
    ]
  },
  etf_quanttype: {
    key: "etf_quanttype",
    label: "Quant Type",
    dataFilter: "etf_quanttype",
    groups: [
      "etf"
    ],
    options: [
      {
        value: "custom_subscription",
        label: "Elite only",
        eliteOnly: true
      }
    ]
  },
  etf_region: {
    key: "etf_region",
    label: "Region",
    dataFilter: "etf_region",
    groups: [
      "etf"
    ],
    options: [
      {
        value: "custom_subscription",
        label: "Elite only",
        eliteOnly: true
      }
    ]
  },
  etf_return: {
    key: "etf_return",
    label: "Annualized Return",
    dataFilter: "etf_return",
    groups: [
      "all",
      "etf"
    ],
    options: [
      {
        value: "",
        label: "Any",
        eliteOnly: false
      },
      {
        value: "1yo0",
        label: "1 Year - Over 0%",
        eliteOnly: false
      },
      {
        value: "1yo10",
        label: "1 Year - Over 10%",
        eliteOnly: false
      },
      {
        value: "1yo25",
        label: "1 Year - Over 25%",
        eliteOnly: false
      },
      {
        value: "1yo05",
        label: "1 Year - Over 5%",
        eliteOnly: false
      },
      {
        value: "1yu10",
        label: "1 Year - Under -10%",
        eliteOnly: false
      },
      {
        value: "1yu25",
        label: "1 Year - Under -25%",
        eliteOnly: false
      },
      {
        value: "1yu05",
        label: "1 Year - Under -5%",
        eliteOnly: false
      },
      {
        value: "1yu0",
        label: "1 Year - Under 0%",
        eliteOnly: false
      },
      {
        value: "3yo0",
        label: "3 Year - Over 0%",
        eliteOnly: false
      },
      {
        value: "3yo10",
        label: "3 Year - Over 10%",
        eliteOnly: false
      },
      {
        value: "3yo25",
        label: "3 Year - Over 25%",
        eliteOnly: false
      },
      {
        value: "3yo05",
        label: "3 Year - Over 5%",
        eliteOnly: false
      },
      {
        value: "3yu10",
        label: "3 Year - Under -10%",
        eliteOnly: false
      },
      {
        value: "3yu25",
        label: "3 Year - Under -25%",
        eliteOnly: false
      },
      {
        value: "3yu05",
        label: "3 Year - Under -5%",
        eliteOnly: false
      },
      {
        value: "3yu0",
        label: "3 Year - Under 0%",
        eliteOnly: false
      },
      {
        value: "5yo0",
        label: "5 Year - Over 0%",
        eliteOnly: false
      },
      {
        value: "5yo10",
        label: "5 Year - Over 10%",
        eliteOnly: false
      },
      {
        value: "5yo25",
        label: "5 Year - Over 25%",
        eliteOnly: false
      },
      {
        value: "5yo05",
        label: "5 Year - Over 5%",
        eliteOnly: false
      },
      {
        value: "5yu10",
        label: "5 Year - Under -10%",
        eliteOnly: false
      },
      {
        value: "5yu25",
        label: "5 Year - Under -25%",
        eliteOnly: false
      },
      {
        value: "5yu05",
        label: "5 Year - Under -5%",
        eliteOnly: false
      },
      {
        value: "5yu0",
        label: "5 Year - Under 0%",
        eliteOnly: false
      },
      {
        value: "custom_subscription",
        label: "More (Elite only)",
        eliteOnly: true
      }
    ]
  },
  etf_sectortheme: {
    key: "etf_sectortheme",
    label: "Sector/Theme",
    dataFilter: "etf_sectortheme",
    groups: [
      "etf"
    ],
    options: [
      {
        value: "custom_subscription",
        label: "Elite only",
        eliteOnly: true
      }
    ]
  },
  etf_sponsor: {
    key: "etf_sponsor",
    label: "Sponsor",
    dataFilter: "etf_sponsor",
    groups: [
      "all",
      "etf"
    ],
    options: [
      {
        value: "",
        label: "Any",
        eliteOnly: false
      },
      {
        value: "21shares",
        label: "21Shares",
        eliteOnly: false
      },
      {
        value: "3edgeassetmanagement",
        label: "3EDGE Asset Management",
        eliteOnly: false
      },
      {
        value: "3fourteensmi",
        label: "3Fourteen & SMI",
        eliteOnly: false
      },
      {
        value: "acsifunds",
        label: "ACSI Funds",
        eliteOnly: false
      },
      {
        value: "acvetf",
        label: "ACV ETF",
        eliteOnly: false
      },
      {
        value: "adaptiveinvestments",
        label: "ADAPTIVE INVESTMENTS",
        eliteOnly: false
      },
      {
        value: "agf",
        label: "AGF",
        eliteOnly: false
      },
      {
        value: "alps",
        label: "ALPS",
        eliteOnly: false
      },
      {
        value: "amgfunds",
        label: "AMG Funds",
        eliteOnly: false
      },
      {
        value: "aotinvest",
        label: "AOT INVEST",
        eliteOnly: false
      },
      {
        value: "arkfunds",
        label: "ARK Funds",
        eliteOnly: false
      },
      {
        value: "arsinvestmentpartners",
        label: "ARS Investment Partners",
        eliteOnly: false
      },
      {
        value: "atacfunds",
        label: "ATAC Funds",
        eliteOnly: false
      },
      {
        value: "axsinvestments",
        label: "AXS Investments",
        eliteOnly: false
      },
      {
        value: "abacusfcfadvisors",
        label: "Abacus FCF Advisors",
        eliteOnly: false
      },
      {
        value: "absoluteinvestmentadvisers",
        label: "Absolute Investment Advisers",
        eliteOnly: false
      },
      {
        value: "academyam",
        label: "Academy AM",
        eliteOnly: false
      },
      {
        value: "accuvestglobaladvisors",
        label: "Accuvest Global Advisors",
        eliteOnly: false
      },
      {
        value: "acquirersfunds",
        label: "Acquirers Funds",
        eliteOnly: false
      },
      {
        value: "acruencecapital",
        label: "Acruence Capital",
        eliteOnly: false
      },
      {
        value: "adaptiv",
        label: "Adaptiv",
        eliteOnly: false
      },
      {
        value: "adasinasocialcapital",
        label: "Adasina Social Capital",
        eliteOnly: false
      },
      {
        value: "advent",
        label: "Advent",
        eliteOnly: false
      },
      {
        value: "advisorshares",
        label: "Advisor Shares",
        eliteOnly: false
      },
      {
        value: "advisorsassetmanagement",
        label: "Advisors Asset Management",
        eliteOnly: false
      },
      {
        value: "akrecapitalmanagement",
        label: "Akre Capital Management",
        eliteOnly: false
      },
      {
        value: "alexisinvests",
        label: "Alexis Invests",
        eliteOnly: false
      },
      {
        value: "alger",
        label: "Alger",
        eliteOnly: false
      },
      {
        value: "alliancebernstein",
        label: "AllianceBernstein",
        eliteOnly: false
      },
      {
        value: "allianzim",
        label: "AllianzIM",
        eliteOnly: false
      },
      {
        value: "allspring",
        label: "Allspring",
        eliteOnly: false
      },
      {
        value: "alphaarchitect",
        label: "Alpha Architect",
        eliteOnly: false
      },
      {
        value: "alphablue",
        label: "Alpha Blue",
        eliteOnly: false
      },
      {
        value: "alphabit",
        label: "AlphaBit",
        eliteOnly: false
      },
      {
        value: "altshares",
        label: "AltShares",
        eliteOnly: false
      },
      {
        value: "altriuscapital",
        label: "Altrius Capital",
        eliteOnly: false
      },
      {
        value: "americanbeacon",
        label: "American Beacon",
        eliteOnly: false
      },
      {
        value: "americancenturyinvestments",
        label: "American Century Investments",
        eliteOnly: false
      },
      {
        value: "amplifyinvestments",
        label: "Amplify Investments",
        eliteOnly: false
      },
      {
        value: "ampliusassetmanagement",
        label: "Amplius Asset Management",
        eliteOnly: false
      },
      {
        value: "anfieldcapitalmanagement",
        label: "Anfield Capital Management",
        eliteOnly: false
      },
      {
        value: "angeloak",
        label: "Angel Oak",
        eliteOnly: false
      },
      {
        value: "anydruscapital",
        label: "Anydrus Capital",
        eliteOnly: false
      },
      {
        value: "appliedfinancefunds",
        label: "Applied Finance Funds",
        eliteOnly: false
      },
      {
        value: "aptuscapitaladvisors",
        label: "Aptus Capital Advisors",
        eliteOnly: false
      },
      {
        value: "archerinvestmentcorporation",
        label: "Archer Investment Corporation",
        eliteOnly: false
      },
      {
        value: "argentcapitalmanagement",
        label: "Argent Capital Management",
        eliteOnly: false
      },
      {
        value: "arin",
        label: "Arin",
        eliteOnly: false
      },
      {
        value: "arlingtonpartners",
        label: "Arlington Partners",
        eliteOnly: false
      },
      {
        value: "armadaetfadvisors",
        label: "Armada ETF Advisors",
        eliteOnly: false
      },
      {
        value: "arrowshares",
        label: "ArrowShares",
        eliteOnly: false
      },
      {
        value: "astoria",
        label: "Astoria",
        eliteOnly: false
      },
      {
        value: "atlascapital",
        label: "Atlas Capital",
        eliteOnly: false
      },
      {
        value: "aztlan",
        label: "Aztlan",
        eliteOnly: false
      },
      {
        value: "bnymellon",
        label: "BNY Mellon",
        eliteOnly: false
      },
      {
        value: "bahlgaynor",
        label: "Bahl & Gaynor",
        eliteOnly: false
      },
      {
        value: "ballastam",
        label: "Ballast AM",
        eliteOnly: false
      },
      {
        value: "bancreek",
        label: "Bancreek",
        eliteOnly: false
      },
      {
        value: "barclays",
        label: "Barclays",
        eliteOnly: false
      },
      {
        value: "barclaysipath",
        label: "Barclays iPath",
        eliteOnly: false
      },
      {
        value: "baroncapital",
        label: "Baron Capital",
        eliteOnly: false
      },
      {
        value: "bastion",
        label: "Bastion",
        eliteOnly: false
      },
      {
        value: "beacon",
        label: "Beacon",
        eliteOnly: false
      },
      {
        value: "beyondinvesting",
        label: "Beyond Investing",
        eliteOnly: false
      },
      {
        value: "bitwise",
        label: "Bitwise",
        eliteOnly: false
      },
      {
        value: "blackrockishares",
        label: "Blackrock (iShares)",
        eliteOnly: false
      },
      {
        value: "bluemonteinvestmentmanagement",
        label: "Bluemonte Investment Management",
        eliteOnly: false
      },
      {
        value: "blueprintfundmanagement",
        label: "Blueprint Fund Management",
        eliteOnly: false
      },
      {
        value: "bondbloxx",
        label: "BondBloxx",
        eliteOnly: false
      },
      {
        value: "brandesinvestment",
        label: "Brandes Investment",
        eliteOnly: false
      },
      {
        value: "brendanwood",
        label: "Brendan Wood",
        eliteOnly: false
      },
      {
        value: "bridgescapital",
        label: "Bridges Capital",
        eliteOnly: false
      },
      {
        value: "bridgeway",
        label: "Bridgeway",
        eliteOnly: false
      },
      {
        value: "brinsmere",
        label: "Brinsmere",
        eliteOnly: false
      },
      {
        value: "brookmontcapital",
        label: "Brookmont Capital",
        eliteOnly: false
      },
      {
        value: "brookstone",
        label: "Brookstone",
        eliteOnly: false
      },
      {
        value: "brownadvisory",
        label: "Brown Advisory",
        eliteOnly: false
      },
      {
        value: "brownbrothersharriman",
        label: "Brown Brothers Harriman",
        eliteOnly: false
      },
      {
        value: "bufferlabs",
        label: "BufferLABS",
        eliteOnly: false
      },
      {
        value: "buildassetmanagement",
        label: "Build Asset Management",
        eliteOnly: false
      },
      {
        value: "burneyinvestment",
        label: "Burney Investment",
        eliteOnly: false
      },
      {
        value: "bushidocapital",
        label: "Bushido Capital",
        eliteOnly: false
      },
      {
        value: "ccm",
        label: "CCM",
        eliteOnly: false
      },
      {
        value: "cotwoadvisors",
        label: "COtwo Advisors",
        eliteOnly: false
      },
      {
        value: "cvafunds",
        label: "CVA Funds",
        eliteOnly: false
      },
      {
        value: "cabanaetf",
        label: "Cabana ETF",
        eliteOnly: false
      },
      {
        value: "calamosinvestments",
        label: "Calamos Investments",
        eliteOnly: false
      },
      {
        value: "cambiarinvestors",
        label: "Cambiar Investors",
        eliteOnly: false
      },
      {
        value: "cambriafunds",
        label: "Cambria Funds",
        eliteOnly: false
      },
      {
        value: "canarycapitalgroup",
        label: "Canary Capital Group",
        eliteOnly: false
      },
      {
        value: "cannellspears",
        label: "Cannell & Spears",
        eliteOnly: false
      },
      {
        value: "capitalgroup",
        label: "Capital Group",
        eliteOnly: false
      },
      {
        value: "carboncollective",
        label: "Carbon Collective",
        eliteOnly: false
      },
      {
        value: "castellangroup",
        label: "Castellan Group",
        eliteOnly: false
      },
      {
        value: "castleark",
        label: "CastleArk",
        eliteOnly: false
      },
      {
        value: "citydifferentinvestments",
        label: "City Different Investments",
        eliteOnly: false
      },
      {
        value: "clockwisecapital",
        label: "Clockwise Capital",
        eliteOnly: false
      },
      {
        value: "cloughcapitalpartners",
        label: "Clough Capital Partners",
        eliteOnly: false
      },
      {
        value: "coastalequitymanagement",
        label: "Coastal Equity Management",
        eliteOnly: false
      },
      {
        value: "cohensteers",
        label: "Cohen & Steers",
        eliteOnly: false
      },
      {
        value: "coinshares",
        label: "CoinShares",
        eliteOnly: false
      },
      {
        value: "columbiathreadneedleinvestments",
        label: "Columbia Threadneedle Investments",
        eliteOnly: false
      },
      {
        value: "concoursecapital",
        label: "Concourse Capital",
        eliteOnly: false
      },
      {
        value: "conductoretf",
        label: "Conductor ETF",
        eliteOnly: false
      },
      {
        value: "congressamc",
        label: "Congress AMC",
        eliteOnly: false
      },
      {
        value: "convergenceinvestmentpartners",
        label: "Convergence Investment Partners",
        eliteOnly: false
      },
      {
        value: "corealternativecapital",
        label: "Core Alternative Capital",
        eliteOnly: false
      },
      {
        value: "corgistrategies",
        label: "Corgi Strategies",
        eliteOnly: false
      },
      {
        value: "cornercap",
        label: "CornerCap",
        eliteOnly: false
      },
      {
        value: "counterpointfunds",
        label: "Counterpoint Funds",
        eliteOnly: false
      },
      {
        value: "crossingbridge",
        label: "CrossingBridge",
        eliteOnly: false
      },
      {
        value: "crossmarkglobalinvestments",
        label: "Crossmark Global Investments",
        eliteOnly: false
      },
      {
        value: "cullen",
        label: "Cullen",
        eliteOnly: false
      },
      {
        value: "cultivarfunds",
        label: "Cultivar Funds",
        eliteOnly: false
      },
      {
        value: "dws",
        label: "DWS",
        eliteOnly: false
      },
      {
        value: "dakotawealth",
        label: "Dakota Wealth",
        eliteOnly: false
      },
      {
        value: "danainvestmentadvisors",
        label: "Dana Investment Advisors",
        eliteOnly: false
      },
      {
        value: "davisadvisors",
        label: "Davis Advisors",
        eliteOnly: false
      },
      {
        value: "dayhagan",
        label: "Day Hagan",
        eliteOnly: false
      },
      {
        value: "daysglobaladvisors",
        label: "Days Global Advisors",
        eliteOnly: false
      },
      {
        value: "deepwateram",
        label: "Deepwater AM",
        eliteOnly: false
      },
      {
        value: "defianceetfs",
        label: "Defiance ETFs",
        eliteOnly: false
      },
      {
        value: "democracyinvestments",
        label: "Democracy Investments",
        eliteOnly: false
      },
      {
        value: "diamondhillcapitalmanagement",
        label: "Diamond Hill Capital Management",
        eliteOnly: false
      },
      {
        value: "dimensional",
        label: "Dimensional",
        eliteOnly: false
      },
      {
        value: "direxionshares",
        label: "Direxion Shares",
        eliteOnly: false
      },
      {
        value: "disciplinefund",
        label: "Discipline Fund",
        eliteOnly: false
      },
      {
        value: "distillatecapital",
        label: "Distillate Capital",
        eliteOnly: false
      },
      {
        value: "dividendassetscapital",
        label: "Dividend Assets Capital",
        eliteOnly: false
      },
      {
        value: "donoghueforlines",
        label: "Donoghue Forlines",
        eliteOnly: false
      },
      {
        value: "doublelinefunds",
        label: "DoubleLine Funds",
        eliteOnly: false
      },
      {
        value: "dracoevolution",
        label: "Draco Evolution",
        eliteOnly: false
      },
      {
        value: "etfmanagersgroup",
        label: "ETF Managers Group",
        eliteOnly: false
      },
      {
        value: "eaglecapital",
        label: "Eagle Capital",
        eliteOnly: false
      },
      {
        value: "elevateshares",
        label: "Elevate Shares",
        eliteOnly: false
      },
      {
        value: "elmpartners",
        label: "Elm Partners",
        eliteOnly: false
      },
      {
        value: "entrepreneurshares",
        label: "EntrepreneurShares",
        eliteOnly: false
      },
      {
        value: "envestnet",
        label: "Envestnet",
        eliteOnly: false
      },
      {
        value: "euclidetf",
        label: "Euclid ETF",
        eliteOnly: false
      },
      {
        value: "evenherd",
        label: "Even Herd",
        eliteOnly: false
      },
      {
        value: "eventideetfs",
        label: "Eventide ETFs",
        eliteOnly: false
      },
      {
        value: "evokeadvisors",
        label: "Evoke Advisors",
        eliteOnly: false
      },
      {
        value: "exchangetradedconcepts",
        label: "Exchange Traded Concepts",
        eliteOnly: false
      },
      {
        value: "fminvestments",
        label: "F/m Investments",
        eliteOnly: false
      },
      {
        value: "fis",
        label: "FIS",
        eliteOnly: false
      },
      {
        value: "fairleadstrategies",
        label: "Fairlead Strategies",
        eliteOnly: false
      },
      {
        value: "federatedhermes",
        label: "Federated Hermes",
        eliteOnly: false
      },
      {
        value: "fidelity",
        label: "Fidelity",
        eliteOnly: false
      },
      {
        value: "firsteagle",
        label: "First Eagle",
        eliteOnly: false
      },
      {
        value: "firstmanhattan",
        label: "First Manhattan",
        eliteOnly: false
      },
      {
        value: "firstpacificadvisors",
        label: "First Pacific Advisors",
        eliteOnly: false
      },
      {
        value: "firsttrust",
        label: "First Trust",
        eliteOnly: false
      },
      {
        value: "flexsharesnortherntrust",
        label: "Flexshares (Northern Trust)",
        eliteOnly: false
      },
      {
        value: "foliobeyond",
        label: "FolioBeyond",
        eliteOnly: false
      },
      {
        value: "formidablefunds",
        label: "Formidable Funds",
        eliteOnly: false
      },
      {
        value: "fortunafunds",
        label: "Fortuna Funds",
        eliteOnly: false
      },
      {
        value: "founderetfs",
        label: "Founder ETFs",
        eliteOnly: false
      },
      {
        value: "franklintempleton",
        label: "Franklin Templeton",
        eliteOnly: false
      },
      {
        value: "freedomday",
        label: "Freedom Day",
        eliteOnly: false
      },
      {
        value: "frontierassetmanagement",
        label: "Frontier Asset Management",
        eliteOnly: false
      },
      {
        value: "fundx",
        label: "FundX",
        eliteOnly: false
      },
      {
        value: "fundsmith",
        label: "Fundsmith",
        eliteOnly: false
      },
      {
        value: "fundstratcapital",
        label: "Fundstrat Capital",
        eliteOnly: false
      },
      {
        value: "futurefunds",
        label: "Future Funds",
        eliteOnly: false
      },
      {
        value: "gamcoinvestors",
        label: "GAMCO Investors",
        eliteOnly: false
      },
      {
        value: "ggmwealthadvisors",
        label: "GGM Wealth Advisors",
        eliteOnly: false
      },
      {
        value: "gmo",
        label: "GMO",
        eliteOnly: false
      },
      {
        value: "gqgpartners",
        label: "GQG Partners",
        eliteOnly: false
      },
      {
        value: "gabelli",
        label: "Gabelli",
        eliteOnly: false
      },
      {
        value: "gadsden",
        label: "Gadsden",
        eliteOnly: false
      },
      {
        value: "gammaroad",
        label: "GammaRoad",
        eliteOnly: false
      },
      {
        value: "gentercapitalmanagement",
        label: "Genter Capital Management",
        eliteOnly: false
      },
      {
        value: "globalx",
        label: "Global X",
        eliteOnly: false
      },
      {
        value: "godbless",
        label: "God Bless",
        eliteOnly: false
      },
      {
        value: "goldeneaglestrategies",
        label: "Golden Eagle Strategies",
        eliteOnly: false
      },
      {
        value: "goldmansachs",
        label: "Goldman Sachs",
        eliteOnly: false
      },
      {
        value: "goosehollow",
        label: "Goose Hollow",
        eliteOnly: false
      },
      {
        value: "gothametf",
        label: "Gotham ETF",
        eliteOnly: false
      },
      {
        value: "graniteshares",
        label: "GraniteShares",
        eliteOnly: false
      },
      {
        value: "grayscale",
        label: "Grayscale",
        eliteOnly: false
      },
      {
        value: "grizzle",
        label: "Grizzle",
        eliteOnly: false
      },
      {
        value: "guinnessatkinson",
        label: "Guinness Atkinson",
        eliteOnly: false
      },
      {
        value: "gurufocus",
        label: "Guru Focus",
        eliteOnly: false
      },
      {
        value: "harborfunds",
        label: "Harbor Funds",
        eliteOnly: false
      },
      {
        value: "harmoniccapital",
        label: "Harmonic Capital",
        eliteOnly: false
      },
      {
        value: "hartfordfunds",
        label: "Hartford Funds",
        eliteOnly: false
      },
      {
        value: "hashdex",
        label: "Hashdex",
        eliteOnly: false
      },
      {
        value: "hedgeyeassetmanagement",
        label: "Hedgeye Asset Management",
        eliteOnly: false
      },
      {
        value: "hennessyfunds",
        label: "Hennessy Funds",
        eliteOnly: false
      },
      {
        value: "hilton",
        label: "Hilton",
        eliteOnly: false
      },
      {
        value: "honeytree",
        label: "Honeytree",
        eliteOnly: false
      },
      {
        value: "horizoninvestments",
        label: "Horizon Investments",
        eliteOnly: false
      },
      {
        value: "horizonkinetics",
        label: "Horizon Kinetics",
        eliteOnly: false
      },
      {
        value: "hotchkiswiley",
        label: "Hotchkis & Wiley",
        eliteOnly: false
      },
      {
        value: "howardcapitalmanagement",
        label: "Howard Capital Management",
        eliteOnly: false
      },
      {
        value: "hoyacapital",
        label: "Hoya Capital",
        eliteOnly: false
      },
      {
        value: "hypatiacapital",
        label: "Hypatia Capital",
        eliteOnly: false
      },
      {
        value: "idxshares",
        label: "IDX Shares",
        eliteOnly: false
      },
      {
        value: "impactshares",
        label: "Impact Shares",
        eliteOnly: false
      },
      {
        value: "indexperts",
        label: "Indexperts",
        eliteOnly: false
      },
      {
        value: "infrastructurecapitaladvisors",
        label: "Infrastructure Capital Advisors",
        eliteOnly: false
      },
      {
        value: "innovatormanagement",
        label: "Innovator Management",
        eliteOnly: false
      },
      {
        value: "inspireinvesting",
        label: "Inspire Investing",
        eliteOnly: false
      },
      {
        value: "intechim",
        label: "Intech IM",
        eliteOnly: false
      },
      {
        value: "intelligentalpha",
        label: "Intelligent Alpha",
        eliteOnly: false
      },
      {
        value: "invesco",
        label: "Invesco",
        eliteOnly: false
      },
      {
        value: "jlens",
        label: "JLens",
        eliteOnly: false
      },
      {
        value: "jpmorganchase",
        label: "JPMorgan Chase",
        eliteOnly: false
      },
      {
        value: "janus",
        label: "Janus",
        eliteOnly: false
      },
      {
        value: "jensen",
        label: "Jensen",
        eliteOnly: false
      },
      {
        value: "johnhancockfunds",
        label: "John Hancock Funds",
        eliteOnly: false
      },
      {
        value: "kkmfinancial",
        label: "KKM Financial",
        eliteOnly: false
      },
      {
        value: "keatinginvestment",
        label: "Keating Investment",
        eliteOnly: false
      },
      {
        value: "kensingtonassetmanagement",
        label: "Kensington Asset Management",
        eliteOnly: false
      },
      {
        value: "kingsbarncapital",
        label: "Kingsbarn Capital",
        eliteOnly: false
      },
      {
        value: "kovitz",
        label: "Kovitz",
        eliteOnly: false
      },
      {
        value: "kraneshares",
        label: "Krane Shares",
        eliteOnly: false
      },
      {
        value: "kurvshares",
        label: "Kurv Shares",
        eliteOnly: false
      },
      {
        value: "lsvassetmanagement",
        label: "LSV Asset Management",
        eliteOnly: false
      },
      {
        value: "laffertengler",
        label: "Laffer Tengler",
        eliteOnly: false
      },
      {
        value: "langarinvestment",
        label: "Langar Investment",
        eliteOnly: false
      },
      {
        value: "lazardassetmanagement",
        label: "Lazard Asset Management",
        eliteOnly: false
      },
      {
        value: "leadershares",
        label: "LeaderShares",
        eliteOnly: false
      },
      {
        value: "leatherbackassetmanagement",
        label: "Leatherback Asset Management",
        eliteOnly: false
      },
      {
        value: "leutholdgroup",
        label: "Leuthold Group",
        eliteOnly: false
      },
      {
        value: "leverageshares",
        label: "Leverage Shares",
        eliteOnly: false
      },
      {
        value: "libertyoneim",
        label: "Liberty One IM",
        eliteOnly: false
      },
      {
        value: "lionshares",
        label: "LionShares",
        eliteOnly: false
      },
      {
        value: "liquidstrategies",
        label: "Liquid Strategies",
        eliteOnly: false
      },
      {
        value: "littleharboradvisors",
        label: "Little Harbor Advisors",
        eliteOnly: false
      },
      {
        value: "logancapital",
        label: "Logan Capital",
        eliteOnly: false
      },
      {
        value: "logiqcapital",
        label: "Logiq Capital",
        eliteOnly: false
      },
      {
        value: "longpondcapital",
        label: "Long Pond Capital",
        eliteOnly: false
      },
      {
        value: "longview",
        label: "Longview",
        eliteOnly: false
      },
      {
        value: "maxetns",
        label: "MAX ETNs",
        eliteOnly: false
      },
      {
        value: "mfs",
        label: "MFS",
        eliteOnly: false
      },
      {
        value: "mkametf",
        label: "MKAM ETF",
        eliteOnly: false
      },
      {
        value: "mohrfunds",
        label: "MOHR Funds",
        eliteOnly: false
      },
      {
        value: "mrbl",
        label: "MRBL",
        eliteOnly: false
      },
      {
        value: "musq",
        label: "MUSQ",
        eliteOnly: false
      },
      {
        value: "madisonfunds",
        label: "Madison Funds",
        eliteOnly: false
      },
      {
        value: "mainmanagement",
        label: "Main Management",
        eliteOnly: false
      },
      {
        value: "mairspower",
        label: "Mairs & Power",
        eliteOnly: false
      },
      {
        value: "mangroup",
        label: "Man Group",
        eliteOnly: false
      },
      {
        value: "manzil",
        label: "Manzil",
        eliteOnly: false
      },
      {
        value: "marketdesk",
        label: "MarketDesk",
        eliteOnly: false
      },
      {
        value: "masoncapital",
        label: "Mason Capital",
        eliteOnly: false
      },
      {
        value: "matrixassetadvisors",
        label: "Matrix Asset Advisors",
        eliteOnly: false
      },
      {
        value: "matthewsasia",
        label: "Matthews Asia",
        eliteOnly: false
      },
      {
        value: "mcelhennysheffield",
        label: "McElhenny Sheffield",
        eliteOnly: false
      },
      {
        value: "measuredriskportfolios",
        label: "Measured Risk Portfolios",
        eliteOnly: false
      },
      {
        value: "merkinvestments",
        label: "Merk Investments",
        eliteOnly: false
      },
      {
        value: "microsectors",
        label: "MicroSectors",
        eliteOnly: false
      },
      {
        value: "militiainvestments",
        label: "Militia Investments",
        eliteOnly: false
      },
      {
        value: "millervaluepartners",
        label: "Miller Value Partners",
        eliteOnly: false
      },
      {
        value: "mitsubishi",
        label: "Mitsubishi",
        eliteOnly: false
      },
      {
        value: "monarchfunds",
        label: "Monarch Funds",
        eliteOnly: false
      },
      {
        value: "morgandempsey",
        label: "Morgan Dempsey",
        eliteOnly: false
      },
      {
        value: "morganstanley",
        label: "Morgan Stanley",
        eliteOnly: false
      },
      {
        value: "motleyfoolassetmanagement",
        label: "Motley Fool Asset Management",
        eliteOnly: false
      },
      {
        value: "myriadassetmanagementadvisors",
        label: "Myriad Asset Management Advisors",
        eliteOnly: false
      },
      {
        value: "neosfunds",
        label: "NEOS Funds",
        eliteOnly: false
      },
      {
        value: "nationalsecurityindex",
        label: "National Security Index",
        eliteOnly: false
      },
      {
        value: "natixis",
        label: "Natixis",
        eliteOnly: false
      },
      {
        value: "neddavisresearch",
        label: "Ned Davis Research",
        eliteOnly: false
      },
      {
        value: "nelsoncapital",
        label: "Nelson Capital",
        eliteOnly: false
      },
      {
        value: "nestyield",
        label: "NestYield",
        eliteOnly: false
      },
      {
        value: "neubergerberman",
        label: "Neuberger Berman",
        eliteOnly: false
      },
      {
        value: "newyorklifeinvestments",
        label: "New York Life Investments",
        eliteOnly: false
      },
      {
        value: "nextgenetf",
        label: "NextGen ETF",
        eliteOnly: false
      },
      {
        value: "nightviewcapital",
        label: "Nightview Capital",
        eliteOnly: false
      },
      {
        value: "nomuragroup",
        label: "Nomura Group",
        eliteOnly: false
      },
      {
        value: "northsquareinvestments",
        label: "North Square Investments",
        eliteOnly: false
      },
      {
        value: "nuveen",
        label: "Nuveen",
        eliteOnly: false
      },
      {
        value: "onefund",
        label: "ONEFUND",
        eliteOnly: false
      },
      {
        value: "otadvisors",
        label: "OT Advisors",
        eliteOnly: false
      },
      {
        value: "otgassetmanagement",
        label: "OTG Asset Management",
        eliteOnly: false
      },
      {
        value: "oakmark",
        label: "Oakmark",
        eliteOnly: false
      },
      {
        value: "obra",
        label: "Obra",
        eliteOnly: false
      },
      {
        value: "oceanpark",
        label: "Ocean Park",
        eliteOnly: false
      },
      {
        value: "oneascentinvestments",
        label: "OneAscent Investments",
        eliteOnly: false
      },
      {
        value: "opalcapital",
        label: "Opal Capital",
        eliteOnly: false
      },
      {
        value: "optimizefinancial",
        label: "Optimize Financial",
        eliteOnly: false
      },
      {
        value: "pgiminvestments",
        label: "PGIM Investments",
        eliteOnly: false
      },
      {
        value: "pimco",
        label: "PIMCO",
        eliteOnly: false
      },
      {
        value: "plfunds",
        label: "PL Funds",
        eliteOnly: false
      },
      {
        value: "pmvcapital",
        label: "PMV Capital",
        eliteOnly: false
      },
      {
        value: "ptassetmanagement",
        label: "PT Asset Management",
        eliteOnly: false
      },
      {
        value: "pacerfinancial",
        label: "Pacer Financial",
        eliteOnly: false
      },
      {
        value: "pacificassetmanagement",
        label: "Pacific Asset Management",
        eliteOnly: false
      },
      {
        value: "palmersquare",
        label: "Palmer Square",
        eliteOnly: false
      },
      {
        value: "panagram",
        label: "Panagram",
        eliteOnly: false
      },
      {
        value: "paraleladvisors",
        label: "Paralel Advisors",
        eliteOnly: false
      },
      {
        value: "parnassus",
        label: "Parnassus",
        eliteOnly: false
      },
      {
        value: "peakshares",
        label: "PeakShares",
        eliteOnly: false
      },
      {
        value: "peerless",
        label: "Peerless",
        eliteOnly: false
      },
      {
        value: "peopartners",
        label: "Peo Partners",
        eliteOnly: false
      },
      {
        value: "pictetassetmanagement",
        label: "Pictet Asset Management",
        eliteOnly: false
      },
      {
        value: "pinnacledynamicfunds",
        label: "Pinnacle Dynamic Funds",
        eliteOnly: false
      },
      {
        value: "planrock",
        label: "PlanRock",
        eliteOnly: false
      },
      {
        value: "pointbridgecapital",
        label: "Point Bridge Capital",
        eliteOnly: false
      },
      {
        value: "polencapitalcredit",
        label: "Polen Capital Credit",
        eliteOnly: false
      },
      {
        value: "portfoliobuildingblock",
        label: "Portfolio Building Block",
        eliteOnly: false
      },
      {
        value: "praxisinvestmentmanagement",
        label: "Praxis Investment Management",
        eliteOnly: false
      },
      {
        value: "precidian",
        label: "Precidian",
        eliteOnly: false
      },
      {
        value: "principalfinancialservices",
        label: "Principal Financial Services",
        eliteOnly: false
      },
      {
        value: "proshares",
        label: "ProShares",
        eliteOnly: false
      },
      {
        value: "procuream",
        label: "ProcureAM",
        eliteOnly: false
      },
      {
        value: "prosperafunds",
        label: "Prospera Funds",
        eliteOnly: false
      },
      {
        value: "q3allseason",
        label: "Q3 All-Season",
        eliteOnly: false
      },
      {
        value: "qrafttechnologies",
        label: "Qraft Technologies",
        eliteOnly: false
      },
      {
        value: "quantify",
        label: "Quantify",
        eliteOnly: false
      },
      {
        value: "rexshares",
        label: "REX Shares",
        eliteOnly: false
      },
      {
        value: "rainwaterequity",
        label: "Rainwater Equity",
        eliteOnly: false
      },
      {
        value: "rangeetfs",
        label: "Range ETFs",
        eliteOnly: false
      },
      {
        value: "rareviewfunds",
        label: "Rareview Funds",
        eliteOnly: false
      },
      {
        value: "rayliant",
        label: "Rayliant",
        eliteOnly: false
      },
      {
        value: "raymondjamesinvestmentmanagement",
        label: "Raymond James Investment Management",
        eliteOnly: false
      },
      {
        value: "reckoner",
        label: "Reckoner",
        eliteOnly: false
      },
      {
        value: "reflectionassetmanagement",
        label: "Reflection Asset Management",
        eliteOnly: false
      },
      {
        value: "regancapital",
        label: "Regan Capital",
        eliteOnly: false
      },
      {
        value: "regentsparkfunds",
        label: "Regents Park Funds",
        eliteOnly: false
      },
      {
        value: "relativesentiment",
        label: "Relative Sentiment",
        eliteOnly: false
      },
      {
        value: "renaissance",
        label: "Renaissance",
        eliteOnly: false
      },
      {
        value: "researchaffiliates",
        label: "Research Affiliates",
        eliteOnly: false
      },
      {
        value: "returnstacked",
        label: "Return Stacked",
        eliteOnly: false
      },
      {
        value: "reverb",
        label: "Reverb",
        eliteOnly: false
      },
      {
        value: "river1",
        label: "River1",
        eliteOnly: false
      },
      {
        value: "rockcreek",
        label: "RockCreek",
        eliteOnly: false
      },
      {
        value: "rockefellerassetmanagement",
        label: "Rockefeller Asset Management",
        eliteOnly: false
      },
      {
        value: "roundhillfinancial",
        label: "Roundhill Financial",
        eliteOnly: false
      },
      {
        value: "runningoak",
        label: "Running Oak",
        eliteOnly: false
      },
      {
        value: "russell",
        label: "Russell",
        eliteOnly: false
      },
      {
        value: "seiinvestmentscompany",
        label: "SEI Investments Company",
        eliteOnly: false
      },
      {
        value: "smartwealth",
        label: "SMART Wealth",
        eliteOnly: false
      },
      {
        value: "spfunds",
        label: "SPFunds",
        eliteOnly: false
      },
      {
        value: "stfmanagement",
        label: "STF Management",
        eliteOnly: false
      },
      {
        value: "swanglobalinvestments",
        label: "SWAN Global Investments",
        eliteOnly: false
      },
      {
        value: "swpinvestmentmanagement",
        label: "SWP Investment Management",
        eliteOnly: false
      },
      {
        value: "sabacapital",
        label: "Saba Capital",
        eliteOnly: false
      },
      {
        value: "sanjacalpha",
        label: "SanJac Alpha",
        eliteOnly: false
      },
      {
        value: "sarmayapartners",
        label: "Sarmaya Partners",
        eliteOnly: false
      },
      {
        value: "scharfinvestments",
        label: "Scharf Investments",
        eliteOnly: false
      },
      {
        value: "schwab",
        label: "Schwab",
        eliteOnly: false
      },
      {
        value: "segallbryanthamill",
        label: "Segall Bryant & Hamill",
        eliteOnly: false
      },
      {
        value: "selectfunds",
        label: "Select Funds",
        eliteOnly: false
      },
      {
        value: "sequoiafinancialgroup",
        label: "Sequoia Financial Group",
        eliteOnly: false
      },
      {
        value: "sheltoncapitalmanagement",
        label: "Shelton Capital Management",
        eliteOnly: false
      },
      {
        value: "simplifyetf",
        label: "Simplify ETF",
        eliteOnly: false
      },
      {
        value: "sirenetf",
        label: "Siren ETF",
        eliteOnly: false
      },
      {
        value: "sofi",
        label: "Sofi",
        eliteOnly: false
      },
      {
        value: "sonicshares",
        label: "SonicShares",
        eliteOnly: false
      },
      {
        value: "soundetf",
        label: "Sound ETF",
        eliteOnly: false
      },
      {
        value: "soundwatch",
        label: "Soundwatch",
        eliteOnly: false
      },
      {
        value: "sovereignscapital",
        label: "Sovereign's Capital",
        eliteOnly: false
      },
      {
        value: "sparklinecapital",
        label: "Sparkline Capital",
        eliteOnly: false
      },
      {
        value: "spearinvest",
        label: "Spear Invest",
        eliteOnly: false
      },
      {
        value: "spinnakeretftrust",
        label: "Spinnaker ETF Trust",
        eliteOnly: false
      },
      {
        value: "splitrock",
        label: "Split Rock",
        eliteOnly: false
      },
      {
        value: "sprottassetmanagement",
        label: "Sprott Asset Management",
        eliteOnly: false
      },
      {
        value: "stancecapital",
        label: "Stance Capital",
        eliteOnly: false
      },
      {
        value: "statestreetspdr",
        label: "State Street (SPDR)",
        eliteOnly: false
      },
      {
        value: "sterlingcapital",
        label: "Sterling Capital",
        eliteOnly: false
      },
      {
        value: "stocksnips",
        label: "StockSnips",
        eliteOnly: false
      },
      {
        value: "stoneridge",
        label: "Stone Ridge",
        eliteOnly: false
      },
      {
        value: "stoneportadvisors",
        label: "Stoneport Advisors",
        eliteOnly: false
      },
      {
        value: "strategasassetmanagement",
        label: "Strategas Asset Management",
        eliteOnly: false
      },
      {
        value: "strategyshares",
        label: "Strategy Shares",
        eliteOnly: false
      },
      {
        value: "stratifiedfunds",
        label: "Stratified Funds",
        eliteOnly: false
      },
      {
        value: "striveassetmanagement",
        label: "Strive Asset Management",
        eliteOnly: false
      },
      {
        value: "subversiveetfs",
        label: "Subversive ETFs",
        eliteOnly: false
      },
      {
        value: "summitglobalinvestments",
        label: "Summit Global Investments",
        eliteOnly: false
      },
      {
        value: "suncoastequitymanagement",
        label: "Suncoast Equity Management",
        eliteOnly: false
      },
      {
        value: "symmetrypartners",
        label: "Symmetry Partners",
        eliteOnly: false
      },
      {
        value: "troweprice",
        label: "T. Rowe Price",
        eliteOnly: false
      },
      {
        value: "tcwgroup",
        label: "TCW Group",
        eliteOnly: false
      },
      {
        value: "thorfinancialtechnologies",
        label: "THOR Financial Technologies",
        eliteOnly: false
      },
      {
        value: "tacticaladvantage",
        label: "Tactical Advantage",
        eliteOnly: false
      },
      {
        value: "tappalpha",
        label: "TappAlpha",
        eliteOnly: false
      },
      {
        value: "tema",
        label: "Tema",
        eliteOnly: false
      },
      {
        value: "teramoadvisors",
        label: "Teramo Advisors",
        eliteOnly: false
      },
      {
        value: "teucrium",
        label: "Teucrium",
        eliteOnly: false
      },
      {
        value: "texascapital",
        label: "Texas Capital",
        eliteOnly: false
      },
      {
        value: "thebahnsengrouptbg",
        label: "The Bahnsen Group (TBG)",
        eliteOnly: false
      },
      {
        value: "themesetfs",
        label: "Themes ETFs",
        eliteOnly: false
      },
      {
        value: "thornburg",
        label: "Thornburg",
        eliteOnly: false
      },
      {
        value: "thrivent",
        label: "Thrivent",
        eliteOnly: false
      },
      {
        value: "tidal",
        label: "Tidal",
        eliteOnly: false
      },
      {
        value: "timessquarecapitalmanagement",
        label: "TimesSquare Capital Management",
        eliteOnly: false
      },
      {
        value: "timothyplan",
        label: "Timothy Plan",
        eliteOnly: false
      },
      {
        value: "toewsfunds",
        label: "Toews Funds",
        eliteOnly: false
      },
      {
        value: "tortoisecapitaladvisors",
        label: "Tortoise Capital Advisors",
        eliteOnly: false
      },
      {
        value: "touchstoneinvestments",
        label: "Touchstone Investments",
        eliteOnly: false
      },
      {
        value: "towleco",
        label: "Towle & Co",
        eliteOnly: false
      },
      {
        value: "tradersai",
        label: "TradersAI",
        eliteOnly: false
      },
      {
        value: "transamerica",
        label: "Transamerica",
        eliteOnly: false
      },
      {
        value: "tremblant",
        label: "Tremblant",
        eliteOnly: false
      },
      {
        value: "trueshares",
        label: "TrueShares",
        eliteOnly: false
      },
      {
        value: "truthsocialfunds",
        label: "Truth Social Funds",
        eliteOnly: false
      },
      {
        value: "tuttletacticalmanagement",
        label: "Tuttle Tactical Management",
        eliteOnly: false
      },
      {
        value: "tweedybrowne",
        label: "Tweedy, Browne",
        eliteOnly: false
      },
      {
        value: "twinoak",
        label: "Twin Oak",
        eliteOnly: false
      },
      {
        value: "usglobalinvestors",
        label: "U.S. Global Investors",
        eliteOnly: false
      },
      {
        value: "ubs",
        label: "UBS",
        eliteOnly: false
      },
      {
        value: "unitedstatescommodityfunds",
        label: "United States Commodity Funds",
        eliteOnly: false
      },
      {
        value: "unlimited",
        label: "Unlimited",
        eliteOnly: false
      },
      {
        value: "vaneckassociatescorporation",
        label: "Van Eck Associates Corporation",
        eliteOnly: false
      },
      {
        value: "vanguard",
        label: "Vanguard",
        eliteOnly: false
      },
      {
        value: "vertassetmanagement",
        label: "Vert Asset Management",
        eliteOnly: false
      },
      {
        value: "vestfinancial",
        label: "Vest Financial",
        eliteOnly: false
      },
      {
        value: "victoryshares",
        label: "VictoryShares",
        eliteOnly: false
      },
      {
        value: "vident",
        label: "Vident",
        eliteOnly: false
      },
      {
        value: "virtusetfsolutions",
        label: "Virtus ETF Solutions",
        eliteOnly: false
      },
      {
        value: "vistashares",
        label: "VistaShares",
        eliteOnly: false
      },
      {
        value: "volatilityshares",
        label: "Volatility Shares",
        eliteOnly: false
      },
      {
        value: "vontobelam",
        label: "Vontobel AM",
        eliteOnly: false
      },
      {
        value: "voyainvestmentmanagement",
        label: "Voya Investment Management",
        eliteOnly: false
      },
      {
        value: "wbishares",
        label: "WBI Shares",
        eliteOnly: false
      },
      {
        value: "websinvestments",
        label: "WEBs Investments",
        eliteOnly: false
      },
      {
        value: "whitewolf",
        label: "WHITEWOLF",
        eliteOnly: false
      },
      {
        value: "wahedinvest",
        label: "Wahed Invest",
        eliteOnly: false
      },
      {
        value: "warrencapitalgroup",
        label: "Warren Capital Group",
        eliteOnly: false
      },
      {
        value: "warrenstreetwealthadvisors",
        label: "Warren Street Wealth Advisors",
        eliteOnly: false
      },
      {
        value: "wayfinder",
        label: "Wayfinder",
        eliteOnly: false
      },
      {
        value: "wealthtrust",
        label: "Wealth Trust",
        eliteOnly: false
      },
      {
        value: "wedbushfunds",
        label: "Wedbush Funds",
        eliteOnly: false
      },
      {
        value: "weitzinvestmentmanagement",
        label: "Weitz Investment Management",
        eliteOnly: false
      },
      {
        value: "westwood",
        label: "Westwood",
        eliteOnly: false
      },
      {
        value: "wisdomfixedincomemanagement",
        label: "Wisdom Fixed Income Management",
        eliteOnly: false
      },
      {
        value: "wisdomtree",
        label: "Wisdom Tree",
        eliteOnly: false
      },
      {
        value: "xsquareetf",
        label: "X-Square ETF",
        eliteOnly: false
      },
      {
        value: "xfunds",
        label: "Xfunds",
        eliteOnly: false
      },
      {
        value: "zacks",
        label: "Zacks",
        eliteOnly: false
      },
      {
        value: "zegaetf",
        label: "Zega ETF",
        eliteOnly: false
      },
      {
        value: "abrdn",
        label: "abrdn",
        eliteOnly: false
      },
      {
        value: "imgpglobalpartner",
        label: "iMGP Global Partner",
        eliteOnly: false
      },
      {
        value: "ireit",
        label: "iREIT",
        eliteOnly: false
      },
      {
        value: "custom_subscription",
        label: "Custom (Elite only)",
        eliteOnly: true
      }
    ]
  },
  etf_structuretype: {
    key: "etf_structuretype",
    label: "Structure Type",
    dataFilter: "etf_structuretype",
    groups: [
      "etf"
    ],
    options: [
      {
        value: "custom_subscription",
        label: "Elite only",
        eliteOnly: true
      }
    ]
  },
  etf_tags: {
    key: "etf_tags",
    label: "Tags",
    dataFilter: "etf_tags",
    groups: [
      "all",
      "etf"
    ],
    options: [
      {
        value: "",
        label: "Any",
        eliteOnly: false
      },
      {
        value: "13f",
        label: "13F",
        eliteOnly: false
      },
      {
        value: "3dprinting",
        label: "3d-printing",
        eliteOnly: false
      },
      {
        value: "5g",
        label: "5G",
        eliteOnly: false
      },
      {
        value: "ai",
        label: "A.I.",
        eliteOnly: false
      },
      {
        value: "aal",
        label: "AAL",
        eliteOnly: false
      },
      {
        value: "aapl",
        label: "AAPL",
        eliteOnly: false
      },
      {
        value: "abnb",
        label: "ABNB",
        eliteOnly: false
      },
      {
        value: "achr",
        label: "ACHR",
        eliteOnly: false
      },
      {
        value: "adbe",
        label: "ADBE",
        eliteOnly: false
      },
      {
        value: "afrm",
        label: "AFRM",
        eliteOnly: false
      },
      {
        value: "alab",
        label: "ALAB",
        eliteOnly: false
      },
      {
        value: "amd",
        label: "AMD",
        eliteOnly: false
      },
      {
        value: "amzn",
        label: "AMZN",
        eliteOnly: false
      },
      {
        value: "anet",
        label: "ANET",
        eliteOnly: false
      },
      {
        value: "apld",
        label: "APLD",
        eliteOnly: false
      },
      {
        value: "app",
        label: "APP",
        eliteOnly: false
      },
      {
        value: "arkk",
        label: "ARKK",
        eliteOnly: false
      },
      {
        value: "arm",
        label: "ARM",
        eliteOnly: false
      },
      {
        value: "asml",
        label: "ASML",
        eliteOnly: false
      },
      {
        value: "asts",
        label: "ASTS",
        eliteOnly: false
      },
      {
        value: "aud",
        label: "AUD",
        eliteOnly: false
      },
      {
        value: "aur",
        label: "AUR",
        eliteOnly: false
      },
      {
        value: "avav",
        label: "AVAV",
        eliteOnly: false
      },
      {
        value: "avgo",
        label: "AVGO",
        eliteOnly: false
      },
      {
        value: "axon",
        label: "AXON",
        eliteOnly: false
      },
      {
        value: "azn",
        label: "AZN",
        eliteOnly: false
      },
      {
        value: "africa",
        label: "Africa",
        eliteOnly: false
      },
      {
        value: "argentina",
        label: "Argentina",
        eliteOnly: false
      },
      {
        value: "asia",
        label: "Asia",
        eliteOnly: false
      },
      {
        value: "asiapacific",
        label: "Asia-Pacific",
        eliteOnly: false
      },
      {
        value: "asiapacificexjapan",
        label: "Asia-Pacific-ex-Japan",
        eliteOnly: false
      },
      {
        value: "asiaexjapan",
        label: "Asia-ex-Japan",
        eliteOnly: false
      },
      {
        value: "australia",
        label: "Australia",
        eliteOnly: false
      },
      {
        value: "austria",
        label: "Austria",
        eliteOnly: false
      },
      {
        value: "ba",
        label: "BA",
        eliteOnly: false
      },
      {
        value: "baba",
        label: "BABA",
        eliteOnly: false
      },
      {
        value: "bbai",
        label: "BBAI",
        eliteOnly: false
      },
      {
        value: "bdc",
        label: "BDC",
        eliteOnly: false
      },
      {
        value: "be",
        label: "BE",
        eliteOnly: false
      },
      {
        value: "bidu",
        label: "BIDU",
        eliteOnly: false
      },
      {
        value: "bkng",
        label: "BKNG",
        eliteOnly: false
      },
      {
        value: "blsh",
        label: "BLSH",
        eliteOnly: false
      },
      {
        value: "bmnr",
        label: "BMNR",
        eliteOnly: false
      },
      {
        value: "bp",
        label: "BP",
        eliteOnly: false
      },
      {
        value: "brkb",
        label: "BRKB",
        eliteOnly: false
      },
      {
        value: "bu",
        label: "BU",
        eliteOnly: false
      },
      {
        value: "bull",
        label: "BULL",
        eliteOnly: false
      },
      {
        value: "belgium",
        label: "Belgium",
        eliteOnly: false
      },
      {
        value: "brazil",
        label: "Brazil",
        eliteOnly: false
      },
      {
        value: "cad",
        label: "CAD",
        eliteOnly: false
      },
      {
        value: "ceg",
        label: "CEG",
        eliteOnly: false
      },
      {
        value: "celh",
        label: "CELH",
        eliteOnly: false
      },
      {
        value: "chf",
        label: "CHF",
        eliteOnly: false
      },
      {
        value: "cifr",
        label: "CIFR",
        eliteOnly: false
      },
      {
        value: "clo",
        label: "CLO",
        eliteOnly: false
      },
      {
        value: "cls",
        label: "CLS",
        eliteOnly: false
      },
      {
        value: "clsk",
        label: "CLSK",
        eliteOnly: false
      },
      {
        value: "cmg",
        label: "CMG",
        eliteOnly: false
      },
      {
        value: "coin",
        label: "COIN",
        eliteOnly: false
      },
      {
        value: "corz",
        label: "CORZ",
        eliteOnly: false
      },
      {
        value: "cost",
        label: "COST",
        eliteOnly: false
      },
      {
        value: "crcl",
        label: "CRCL",
        eliteOnly: false
      },
      {
        value: "crdo",
        label: "CRDO",
        eliteOnly: false
      },
      {
        value: "crm",
        label: "CRM",
        eliteOnly: false
      },
      {
        value: "crwd",
        label: "CRWD",
        eliteOnly: false
      },
      {
        value: "crwv",
        label: "CRWV",
        eliteOnly: false
      },
      {
        value: "csco",
        label: "CSCO",
        eliteOnly: false
      },
      {
        value: "cvna",
        label: "CVNA",
        eliteOnly: false
      },
      {
        value: "canada",
        label: "Canada",
        eliteOnly: false
      },
      {
        value: "chile",
        label: "Chile",
        eliteOnly: false
      },
      {
        value: "china",
        label: "China",
        eliteOnly: false
      },
      {
        value: "colombia",
        label: "Colombia",
        eliteOnly: false
      },
      {
        value: "dash",
        label: "DASH",
        eliteOnly: false
      },
      {
        value: "dax",
        label: "DAX",
        eliteOnly: false
      },
      {
        value: "ddog",
        label: "DDOG",
        eliteOnly: false
      },
      {
        value: "dell",
        label: "DELL",
        eliteOnly: false
      },
      {
        value: "dis",
        label: "DIS",
        eliteOnly: false
      },
      {
        value: "djia",
        label: "DJIA",
        eliteOnly: false
      },
      {
        value: "djt",
        label: "DJT",
        eliteOnly: false
      },
      {
        value: "dkng",
        label: "DKNG",
        eliteOnly: false
      },
      {
        value: "duol",
        label: "DUOL",
        eliteOnly: false
      },
      {
        value: "denmark",
        label: "Denmark",
        eliteOnly: false
      },
      {
        value: "developed",
        label: "Developed",
        eliteOnly: false
      },
      {
        value: "developedexjapan",
        label: "Developed-ex-Japan",
        eliteOnly: false
      },
      {
        value: "developedexus",
        label: "Developed-ex-U.S.",
        eliteOnly: false
      },
      {
        value: "eafe",
        label: "EAFE",
        eliteOnly: false
      },
      {
        value: "enph",
        label: "ENPH",
        eliteOnly: false
      },
      {
        value: "esg",
        label: "ESG",
        eliteOnly: false
      },
      {
        value: "etfs",
        label: "ETFs",
        eliteOnly: false
      },
      {
        value: "etor",
        label: "ETOR",
        eliteOnly: false
      },
      {
        value: "eur",
        label: "EUR",
        eliteOnly: false
      },
      {
        value: "emerging",
        label: "Emerging",
        eliteOnly: false
      },
      {
        value: "emergingexchina",
        label: "Emerging-ex-China",
        eliteOnly: false
      },
      {
        value: "europe",
        label: "Europe",
        eliteOnly: false
      },
      {
        value: "eurozone",
        label: "Eurozone",
        eliteOnly: false
      },
      {
        value: "f",
        label: "F",
        eliteOnly: false
      },
      {
        value: "fang",
        label: "FANG",
        eliteOnly: false
      },
      {
        value: "fig",
        label: "FIG",
        eliteOnly: false
      },
      {
        value: "fly",
        label: "FLY",
        eliteOnly: false
      },
      {
        value: "futu",
        label: "FUTU",
        eliteOnly: false
      },
      {
        value: "finland",
        label: "Finland",
        eliteOnly: false
      },
      {
        value: "france",
        label: "France",
        eliteOnly: false
      },
      {
        value: "gbp",
        label: "GBP",
        eliteOnly: false
      },
      {
        value: "gemi",
        label: "GEMI",
        eliteOnly: false
      },
      {
        value: "gev",
        label: "GEV",
        eliteOnly: false
      },
      {
        value: "gevg",
        label: "GEVG",
        eliteOnly: false
      },
      {
        value: "gld",
        label: "GLD",
        eliteOnly: false
      },
      {
        value: "glxy",
        label: "GLXY",
        eliteOnly: false
      },
      {
        value: "gme",
        label: "GME",
        eliteOnly: false
      },
      {
        value: "googl",
        label: "GOOGL",
        eliteOnly: false
      },
      {
        value: "grab",
        label: "GRAB",
        eliteOnly: false
      },
      {
        value: "gs",
        label: "GS",
        eliteOnly: false
      },
      {
        value: "gsk",
        label: "GSK",
        eliteOnly: false
      },
      {
        value: "germany",
        label: "Germany",
        eliteOnly: false
      },
      {
        value: "global",
        label: "Global",
        eliteOnly: false
      },
      {
        value: "globalexus",
        label: "Global-ex-U.S.",
        eliteOnly: false
      },
      {
        value: "greece",
        label: "Greece",
        eliteOnly: false
      },
      {
        value: "hims",
        label: "HIMS",
        eliteOnly: false
      },
      {
        value: "hood",
        label: "HOOD",
        eliteOnly: false
      },
      {
        value: "hsbc",
        label: "HSBC",
        eliteOnly: false
      },
      {
        value: "honkkong",
        label: "Honk-Kong",
        eliteOnly: false
      },
      {
        value: "it",
        label: "I.T.",
        eliteOnly: false
      },
      {
        value: "ibit",
        label: "IBIT",
        eliteOnly: false
      },
      {
        value: "intc",
        label: "INTC",
        eliteOnly: false
      },
      {
        value: "ionq",
        label: "IONQ",
        eliteOnly: false
      },
      {
        value: "ipo",
        label: "IPO",
        eliteOnly: false
      },
      {
        value: "iren",
        label: "IREN",
        eliteOnly: false
      },
      {
        value: "isrg",
        label: "ISRG",
        eliteOnly: false
      },
      {
        value: "iceland",
        label: "Iceland",
        eliteOnly: false
      },
      {
        value: "india",
        label: "India",
        eliteOnly: false
      },
      {
        value: "indonesia",
        label: "Indonesia",
        eliteOnly: false
      },
      {
        value: "international",
        label: "International",
        eliteOnly: false
      },
      {
        value: "ireland",
        label: "Ireland",
        eliteOnly: false
      },
      {
        value: "israel",
        label: "Israel",
        eliteOnly: false
      },
      {
        value: "italy",
        label: "Italy",
        eliteOnly: false
      },
      {
        value: "jd",
        label: "JD",
        eliteOnly: false
      },
      {
        value: "joby",
        label: "JOBY",
        eliteOnly: false
      },
      {
        value: "jpm",
        label: "JPM",
        eliteOnly: false
      },
      {
        value: "jpy",
        label: "JPY",
        eliteOnly: false
      },
      {
        value: "japan",
        label: "Japan",
        eliteOnly: false
      },
      {
        value: "ktos",
        label: "KTOS",
        eliteOnly: false
      },
      {
        value: "kuwait",
        label: "Kuwait",
        eliteOnly: false
      },
      {
        value: "lac",
        label: "LAC",
        eliteOnly: false
      },
      {
        value: "lcid",
        label: "LCID",
        eliteOnly: false
      },
      {
        value: "link",
        label: "LINK",
        eliteOnly: false
      },
      {
        value: "lly",
        label: "LLY",
        eliteOnly: false
      },
      {
        value: "lmnd",
        label: "LMND",
        eliteOnly: false
      },
      {
        value: "lmt",
        label: "LMT",
        eliteOnly: false
      },
      {
        value: "lrcx",
        label: "LRCX",
        eliteOnly: false
      },
      {
        value: "lulu",
        label: "LULU",
        eliteOnly: false
      },
      {
        value: "lyft",
        label: "LYFT",
        eliteOnly: false
      },
      {
        value: "latinamerica",
        label: "Latin-America",
        eliteOnly: false
      },
      {
        value: "ma",
        label: "M&A",
        eliteOnly: false
      },
      {
        value: "mara",
        label: "MARA",
        eliteOnly: false
      },
      {
        value: "mbs",
        label: "MBS",
        eliteOnly: false
      },
      {
        value: "mdb",
        label: "MDB",
        eliteOnly: false
      },
      {
        value: "meli",
        label: "MELI",
        eliteOnly: false
      },
      {
        value: "meta",
        label: "META",
        eliteOnly: false
      },
      {
        value: "mlp",
        label: "MLP",
        eliteOnly: false
      },
      {
        value: "mp",
        label: "MP",
        eliteOnly: false
      },
      {
        value: "mrvl",
        label: "MRVL",
        eliteOnly: false
      },
      {
        value: "msft",
        label: "MSFT",
        eliteOnly: false
      },
      {
        value: "mstr",
        label: "MSTR",
        eliteOnly: false
      },
      {
        value: "mu",
        label: "MU",
        eliteOnly: false
      },
      {
        value: "malaysia",
        label: "Malaysia",
        eliteOnly: false
      },
      {
        value: "mexico",
        label: "Mexico",
        eliteOnly: false
      },
      {
        value: "nbis",
        label: "NBIS",
        eliteOnly: false
      },
      {
        value: "nem",
        label: "NEM",
        eliteOnly: false
      },
      {
        value: "net",
        label: "NET",
        eliteOnly: false
      },
      {
        value: "nflx",
        label: "NFLX",
        eliteOnly: false
      },
      {
        value: "nne",
        label: "NNE",
        eliteOnly: false
      },
      {
        value: "now",
        label: "NOW",
        eliteOnly: false
      },
      {
        value: "nu",
        label: "NU",
        eliteOnly: false
      },
      {
        value: "nvda",
        label: "NVDA",
        eliteOnly: false
      },
      {
        value: "nvo",
        label: "NVO",
        eliteOnly: false
      },
      {
        value: "nvts",
        label: "NVTS",
        eliteOnly: false
      },
      {
        value: "nasdaqcomposite",
        label: "Nasdaq-composite",
        eliteOnly: false
      },
      {
        value: "nasdaq100",
        label: "Nasdaq100",
        eliteOnly: false
      },
      {
        value: "netherlands",
        label: "Netherlands",
        eliteOnly: false
      },
      {
        value: "newzealand",
        label: "New-Zealand",
        eliteOnly: false
      },
      {
        value: "nikkei400",
        label: "Nikkei-400",
        eliteOnly: false
      },
      {
        value: "northamerica",
        label: "North-America",
        eliteOnly: false
      },
      {
        value: "norway",
        label: "Norway",
        eliteOnly: false
      },
      {
        value: "oklo",
        label: "OKLO",
        eliteOnly: false
      },
      {
        value: "okta",
        label: "OKTA",
        eliteOnly: false
      },
      {
        value: "open",
        label: "OPEN",
        eliteOnly: false
      },
      {
        value: "orcl",
        label: "ORCL",
        eliteOnly: false
      },
      {
        value: "oscr",
        label: "OSCR",
        eliteOnly: false
      },
      {
        value: "panw",
        label: "PANW",
        eliteOnly: false
      },
      {
        value: "pdd",
        label: "PDD",
        eliteOnly: false
      },
      {
        value: "pltr",
        label: "PLTR",
        eliteOnly: false
      },
      {
        value: "pm",
        label: "PM",
        eliteOnly: false
      },
      {
        value: "pony",
        label: "PONY",
        eliteOnly: false
      },
      {
        value: "pypl",
        label: "PYPL",
        eliteOnly: false
      },
      {
        value: "peru",
        label: "Peru",
        eliteOnly: false
      },
      {
        value: "poland",
        label: "Poland",
        eliteOnly: false
      },
      {
        value: "qbts",
        label: "QBTS",
        eliteOnly: false
      },
      {
        value: "qcom",
        label: "QCOM",
        eliteOnly: false
      },
      {
        value: "qqq",
        label: "QQQ",
        eliteOnly: false
      },
      {
        value: "qs",
        label: "QS",
        eliteOnly: false
      },
      {
        value: "qsx",
        label: "QSX",
        eliteOnly: false
      },
      {
        value: "qubt",
        label: "QUBT",
        eliteOnly: false
      },
      {
        value: "quatar",
        label: "Quatar",
        eliteOnly: false
      },
      {
        value: "rd",
        label: "R&D",
        eliteOnly: false
      },
      {
        value: "rblx",
        label: "RBLX",
        eliteOnly: false
      },
      {
        value: "rddt",
        label: "RDDT",
        eliteOnly: false
      },
      {
        value: "reits",
        label: "REITs",
        eliteOnly: false
      },
      {
        value: "rgti",
        label: "RGTI",
        eliteOnly: false
      },
      {
        value: "riot",
        label: "RIOT",
        eliteOnly: false
      },
      {
        value: "rivn",
        label: "RIVN",
        eliteOnly: false
      },
      {
        value: "rklb",
        label: "RKLB",
        eliteOnly: false
      },
      {
        value: "rtx",
        label: "RTX",
        eliteOnly: false
      },
      {
        value: "russell1000",
        label: "Russell-1000",
        eliteOnly: false
      },
      {
        value: "russell200",
        label: "Russell-200",
        eliteOnly: false
      },
      {
        value: "russell2000",
        label: "Russell-2000",
        eliteOnly: false
      },
      {
        value: "russell2500",
        label: "Russell-2500",
        eliteOnly: false
      },
      {
        value: "russell3000",
        label: "Russell-3000",
        eliteOnly: false
      },
      {
        value: "sap",
        label: "SAP",
        eliteOnly: false
      },
      {
        value: "sats",
        label: "SATS",
        eliteOnly: false
      },
      {
        value: "sbet",
        label: "SBET",
        eliteOnly: false
      },
      {
        value: "sbux",
        label: "SBUX",
        eliteOnly: false
      },
      {
        value: "shel",
        label: "SHEL",
        eliteOnly: false
      },
      {
        value: "shop",
        label: "SHOP",
        eliteOnly: false
      },
      {
        value: "slv",
        label: "SLV",
        eliteOnly: false
      },
      {
        value: "smci",
        label: "SMCI",
        eliteOnly: false
      },
      {
        value: "smr",
        label: "SMR",
        eliteOnly: false
      },
      {
        value: "snow",
        label: "SNOW",
        eliteOnly: false
      },
      {
        value: "snpx",
        label: "SNPX",
        eliteOnly: false
      },
      {
        value: "sofi",
        label: "SOFI",
        eliteOnly: false
      },
      {
        value: "soun",
        label: "SOUN",
        eliteOnly: false
      },
      {
        value: "sp100",
        label: "SP100",
        eliteOnly: false
      },
      {
        value: "sp1000",
        label: "SP1000",
        eliteOnly: false
      },
      {
        value: "sp1500",
        label: "SP1500",
        eliteOnly: false
      },
      {
        value: "sp400",
        label: "SP400",
        eliteOnly: false
      },
      {
        value: "sp500",
        label: "SP500",
        eliteOnly: false
      },
      {
        value: "sp600",
        label: "SP600",
        eliteOnly: false
      },
      {
        value: "spac",
        label: "SPAC",
        eliteOnly: false
      },
      {
        value: "spot",
        label: "SPOT",
        eliteOnly: false
      },
      {
        value: "spy",
        label: "SPY",
        eliteOnly: false
      },
      {
        value: "srpt",
        label: "SRPT",
        eliteOnly: false
      },
      {
        value: "sthh",
        label: "STHH",
        eliteOnly: false
      },
      {
        value: "saudiarabia",
        label: "Saudi-Arabia",
        eliteOnly: false
      },
      {
        value: "singapore",
        label: "Singapore",
        eliteOnly: false
      },
      {
        value: "southafrica",
        label: "South-Africa",
        eliteOnly: false
      },
      {
        value: "southkorea",
        label: "South-Korea",
        eliteOnly: false
      },
      {
        value: "spain",
        label: "Spain",
        eliteOnly: false
      },
      {
        value: "sweden",
        label: "Sweden",
        eliteOnly: false
      },
      {
        value: "switzerland",
        label: "Switzerland",
        eliteOnly: false
      },
      {
        value: "tem",
        label: "TEM",
        eliteOnly: false
      },
      {
        value: "ter",
        label: "TER",
        eliteOnly: false
      },
      {
        value: "tips",
        label: "TIPS",
        eliteOnly: false
      },
      {
        value: "tm",
        label: "TM",
        eliteOnly: false
      },
      {
        value: "tsla",
        label: "TSLA",
        eliteOnly: false
      },
      {
        value: "tsm",
        label: "TSM",
        eliteOnly: false
      },
      {
        value: "ttd",
        label: "TTD",
        eliteOnly: false
      },
      {
        value: "taiwan",
        label: "Taiwan",
        eliteOnly: false
      },
      {
        value: "thailand",
        label: "Thailand",
        eliteOnly: false
      },
      {
        value: "turkey",
        label: "Turkey",
        eliteOnly: false
      },
      {
        value: "u",
        label: "U",
        eliteOnly: false
      },
      {
        value: "uk",
        label: "U.K.",
        eliteOnly: false
      },
      {
        value: "us",
        label: "U.S.",
        eliteOnly: false
      },
      {
        value: "uae",
        label: "UAE",
        eliteOnly: false
      },
      {
        value: "uber",
        label: "UBER",
        eliteOnly: false
      },
      {
        value: "unh",
        label: "UNH",
        eliteOnly: false
      },
      {
        value: "unhw",
        label: "UNHW",
        eliteOnly: false
      },
      {
        value: "ups",
        label: "UPS",
        eliteOnly: false
      },
      {
        value: "upst",
        label: "UPST",
        eliteOnly: false
      },
      {
        value: "upxi",
        label: "UPXI",
        eliteOnly: false
      },
      {
        value: "usd",
        label: "USD",
        eliteOnly: false
      },
      {
        value: "uso",
        label: "USO",
        eliteOnly: false
      },
      {
        value: "voyg",
        label: "VOYG",
        eliteOnly: false
      },
      {
        value: "vrt",
        label: "VRT",
        eliteOnly: false
      },
      {
        value: "vst",
        label: "VST",
        eliteOnly: false
      },
      {
        value: "vietnam",
        label: "Vietnam",
        eliteOnly: false
      },
      {
        value: "wmt",
        label: "WMT",
        eliteOnly: false
      },
      {
        value: "wulf",
        label: "WULF",
        eliteOnly: false
      },
      {
        value: "xom",
        label: "XOM",
        eliteOnly: false
      },
      {
        value: "xyz",
        label: "XYZ",
        eliteOnly: false
      },
      {
        value: "aerospacedefense",
        label: "aerospace-defense",
        eliteOnly: false
      },
      {
        value: "aggressive",
        label: "aggressive",
        eliteOnly: false
      },
      {
        value: "agriculture",
        label: "agriculture",
        eliteOnly: false
      },
      {
        value: "aircraft",
        label: "aircraft",
        eliteOnly: false
      },
      {
        value: "airlines",
        label: "airlines",
        eliteOnly: false
      },
      {
        value: "alcoholtobacco",
        label: "alcohol-tobacco",
        eliteOnly: false
      },
      {
        value: "assetrotation",
        label: "asset-rotation",
        eliteOnly: false
      },
      {
        value: "autoindustry",
        label: "auto-industry",
        eliteOnly: false
      },
      {
        value: "autocallable",
        label: "autocallable",
        eliteOnly: false
      },
      {
        value: "automation",
        label: "automation",
        eliteOnly: false
      },
      {
        value: "autonomousvehicles",
        label: "autonomous-vehicles",
        eliteOnly: false
      },
      {
        value: "banks",
        label: "banks",
        eliteOnly: false
      },
      {
        value: "batteries",
        label: "batteries",
        eliteOnly: false
      },
      {
        value: "betting",
        label: "betting",
        eliteOnly: false
      },
      {
        value: "bigdata",
        label: "big-data",
        eliteOnly: false
      },
      {
        value: "biotechnology",
        label: "biotechnology",
        eliteOnly: false
      },
      {
        value: "bitcoin",
        label: "bitcoin",
        eliteOnly: false
      },
      {
        value: "blockchain",
        label: "blockchain",
        eliteOnly: false
      },
      {
        value: "bluechip",
        label: "blue-chip",
        eliteOnly: false
      },
      {
        value: "bonds",
        label: "bonds",
        eliteOnly: false
      },
      {
        value: "brokerage",
        label: "brokerage",
        eliteOnly: false
      },
      {
        value: "buffer",
        label: "buffer",
        eliteOnly: false
      },
      {
        value: "buyback",
        label: "buyback",
        eliteOnly: false
      },
      {
        value: "cannabis",
        label: "cannabis",
        eliteOnly: false
      },
      {
        value: "capitalmarkets",
        label: "capital-markets",
        eliteOnly: false
      },
      {
        value: "carbonallowances",
        label: "carbon-allowances",
        eliteOnly: false
      },
      {
        value: "carbonlow",
        label: "carbon-low",
        eliteOnly: false
      },
      {
        value: "cashcow",
        label: "cash-cow",
        eliteOnly: false
      },
      {
        value: "casino",
        label: "casino",
        eliteOnly: false
      },
      {
        value: "catholicvalues",
        label: "catholic-values",
        eliteOnly: false
      },
      {
        value: "cleanenergy",
        label: "clean-energy",
        eliteOnly: false
      },
      {
        value: "climatechange",
        label: "climate-change",
        eliteOnly: false
      },
      {
        value: "clinicaltrials",
        label: "clinical-trials",
        eliteOnly: false
      },
      {
        value: "cloudcomputing",
        label: "cloud-computing",
        eliteOnly: false
      },
      {
        value: "coal",
        label: "coal",
        eliteOnly: false
      },
      {
        value: "cobalt",
        label: "cobalt",
        eliteOnly: false
      },
      {
        value: "commodity",
        label: "commodity",
        eliteOnly: false
      },
      {
        value: "communicationservices",
        label: "communication-services",
        eliteOnly: false
      },
      {
        value: "communitybanks",
        label: "community-banks",
        eliteOnly: false
      },
      {
        value: "conservative",
        label: "conservative",
        eliteOnly: false
      },
      {
        value: "consumer",
        label: "consumer",
        eliteOnly: false
      },
      {
        value: "consumerdiscretionary",
        label: "consumer-discretionary",
        eliteOnly: false
      },
      {
        value: "consumerstaples",
        label: "consumer-staples",
        eliteOnly: false
      },
      {
        value: "convertiblesecurities",
        label: "convertible-securities",
        eliteOnly: false
      },
      {
        value: "copper",
        label: "copper",
        eliteOnly: false
      },
      {
        value: "corn",
        label: "corn",
        eliteOnly: false
      },
      {
        value: "corporatebonds",
        label: "corporate-bonds",
        eliteOnly: false
      },
      {
        value: "coveredcall",
        label: "covered-call",
        eliteOnly: false
      },
      {
        value: "crypto",
        label: "crypto",
        eliteOnly: false
      },
      {
        value: "cryptospot",
        label: "crypto-spot",
        eliteOnly: false
      },
      {
        value: "currencies",
        label: "currencies",
        eliteOnly: false
      },
      {
        value: "currency",
        label: "currency",
        eliteOnly: false
      },
      {
        value: "currencybonds",
        label: "currency-bonds",
        eliteOnly: false
      },
      {
        value: "customer",
        label: "customer",
        eliteOnly: false
      },
      {
        value: "cybersecurity",
        label: "cyber-security",
        eliteOnly: false
      },
      {
        value: "datacenters",
        label: "data-centers",
        eliteOnly: false
      },
      {
        value: "debt",
        label: "debt",
        eliteOnly: false
      },
      {
        value: "debtsecurities",
        label: "debt-securities",
        eliteOnly: false
      },
      {
        value: "democrats",
        label: "democrats",
        eliteOnly: false
      },
      {
        value: "derivatives",
        label: "derivatives",
        eliteOnly: false
      },
      {
        value: "digitalinfrastructure",
        label: "digital-infrastructure",
        eliteOnly: false
      },
      {
        value: "digitalpayments",
        label: "digital-payments",
        eliteOnly: false
      },
      {
        value: "disruptive",
        label: "disruptive",
        eliteOnly: false
      },
      {
        value: "dividend",
        label: "dividend",
        eliteOnly: false
      },
      {
        value: "dividendgrowth",
        label: "dividend-growth",
        eliteOnly: false
      },
      {
        value: "dividendweight",
        label: "dividend-weight",
        eliteOnly: false
      },
      {
        value: "dodge",
        label: "dodge",
        eliteOnly: false
      },
      {
        value: "doge",
        label: "doge",
        eliteOnly: false
      },
      {
        value: "drones",
        label: "drones",
        eliteOnly: false
      },
      {
        value: "drybulk",
        label: "dry-bulk",
        eliteOnly: false
      },
      {
        value: "ecommerce",
        label: "e-commerce",
        eliteOnly: false
      },
      {
        value: "esports",
        label: "e-sports",
        eliteOnly: false
      },
      {
        value: "electricvehicles",
        label: "electric-vehicles",
        eliteOnly: false
      },
      {
        value: "electricity",
        label: "electricity",
        eliteOnly: false
      },
      {
        value: "energy",
        label: "energy",
        eliteOnly: false
      },
      {
        value: "energymanagement",
        label: "energy-management",
        eliteOnly: false
      },
      {
        value: "energystorage",
        label: "energy-storage",
        eliteOnly: false
      },
      {
        value: "entertainment",
        label: "entertainment",
        eliteOnly: false
      },
      {
        value: "environmental",
        label: "environmental",
        eliteOnly: false
      },
      {
        value: "equalweight",
        label: "equal-weight",
        eliteOnly: false
      },
      {
        value: "equity",
        label: "equity",
        eliteOnly: false
      },
      {
        value: "ethereum",
        label: "ethereum",
        eliteOnly: false
      },
      {
        value: "exenergy",
        label: "ex-energy",
        eliteOnly: false
      },
      {
        value: "exfinancial",
        label: "ex-financial",
        eliteOnly: false
      },
      {
        value: "exfossilfuels",
        label: "ex-fossil-fuels",
        eliteOnly: false
      },
      {
        value: "exhealthcare",
        label: "ex-healthcare",
        eliteOnly: false
      },
      {
        value: "extechnology",
        label: "ex-technology",
        eliteOnly: false
      },
      {
        value: "exchanges",
        label: "exchanges",
        eliteOnly: false
      },
      {
        value: "factorrotation",
        label: "factor-rotation",
        eliteOnly: false
      },
      {
        value: "financial",
        label: "financial",
        eliteOnly: false
      },
      {
        value: "fintech",
        label: "fintech",
        eliteOnly: false
      },
      {
        value: "fixedincome",
        label: "fixed-income",
        eliteOnly: false
      },
      {
        value: "fixedperiod",
        label: "fixed-period",
        eliteOnly: false
      },
      {
        value: "floatingrate",
        label: "floating-rate",
        eliteOnly: false
      },
      {
        value: "food",
        label: "food",
        eliteOnly: false
      },
      {
        value: "foodbeverage",
        label: "food-beverage",
        eliteOnly: false
      },
      {
        value: "fossilfuels",
        label: "fossil-fuels",
        eliteOnly: false
      },
      {
        value: "fundamental",
        label: "fundamental",
        eliteOnly: false
      },
      {
        value: "fundamentalweight",
        label: "fundamental-weight",
        eliteOnly: false
      },
      {
        value: "futures",
        label: "futures",
        eliteOnly: false
      },
      {
        value: "gaming",
        label: "gaming",
        eliteOnly: false
      },
      {
        value: "gender",
        label: "gender",
        eliteOnly: false
      },
      {
        value: "genomics",
        label: "genomics",
        eliteOnly: false
      },
      {
        value: "gold",
        label: "gold",
        eliteOnly: false
      },
      {
        value: "goldminers",
        label: "gold-miners",
        eliteOnly: false
      },
      {
        value: "governmentbonds",
        label: "government-bonds",
        eliteOnly: false
      },
      {
        value: "growth",
        label: "growth",
        eliteOnly: false
      },
      {
        value: "hardware",
        label: "hardware",
        eliteOnly: false
      },
      {
        value: "healthcare",
        label: "healthcare",
        eliteOnly: false
      },
      {
        value: "hedera",
        label: "hedera",
        eliteOnly: false
      },
      {
        value: "hedgecurrency",
        label: "hedge-currency",
        eliteOnly: false
      },
      {
        value: "hedgefund",
        label: "hedge-fund",
        eliteOnly: false
      },
      {
        value: "hedgeinflation",
        label: "hedge-inflation",
        eliteOnly: false
      },
      {
        value: "hedgerates",
        label: "hedge-rates",
        eliteOnly: false
      },
      {
        value: "hedgerisk",
        label: "hedge-risk",
        eliteOnly: false
      },
      {
        value: "highbeta",
        label: "high-beta",
        eliteOnly: false
      },
      {
        value: "highyield",
        label: "high-yield",
        eliteOnly: false
      },
      {
        value: "homeconstruction",
        label: "home-construction",
        eliteOnly: false
      },
      {
        value: "hotel",
        label: "hotel",
        eliteOnly: false
      },
      {
        value: "hydrogen",
        label: "hydrogen",
        eliteOnly: false
      },
      {
        value: "income",
        label: "income",
        eliteOnly: false
      },
      {
        value: "industrials",
        label: "industrials",
        eliteOnly: false
      },
      {
        value: "inflation",
        label: "inflation",
        eliteOnly: false
      },
      {
        value: "infrastructure",
        label: "infrastructure",
        eliteOnly: false
      },
      {
        value: "innovation",
        label: "innovation",
        eliteOnly: false
      },
      {
        value: "insurance",
        label: "insurance",
        eliteOnly: false
      },
      {
        value: "internet",
        label: "internet",
        eliteOnly: false
      },
      {
        value: "internetofthings",
        label: "internet-of-things",
        eliteOnly: false
      },
      {
        value: "inverse",
        label: "inverse",
        eliteOnly: false
      },
      {
        value: "investmentgrade",
        label: "investment-grade",
        eliteOnly: false
      },
      {
        value: "largecap",
        label: "large-cap",
        eliteOnly: false
      },
      {
        value: "leadership",
        label: "leadership",
        eliteOnly: false
      },
      {
        value: "leverage",
        label: "leverage",
        eliteOnly: false
      },
      {
        value: "litecoin",
        label: "litecoin",
        eliteOnly: false
      },
      {
        value: "lithium",
        label: "lithium",
        eliteOnly: false
      },
      {
        value: "loans",
        label: "loans",
        eliteOnly: false
      },
      {
        value: "longshort",
        label: "long-short",
        eliteOnly: false
      },
      {
        value: "luxury",
        label: "luxury",
        eliteOnly: false
      },
      {
        value: "machinelearning",
        label: "machine-learning",
        eliteOnly: false
      },
      {
        value: "macro",
        label: "macro",
        eliteOnly: false
      },
      {
        value: "marketsentiment",
        label: "market-sentiment",
        eliteOnly: false
      },
      {
        value: "materials",
        label: "materials",
        eliteOnly: false
      },
      {
        value: "media",
        label: "media",
        eliteOnly: false
      },
      {
        value: "medical",
        label: "medical",
        eliteOnly: false
      },
      {
        value: "megacap",
        label: "mega-cap",
        eliteOnly: false
      },
      {
        value: "metals",
        label: "metals",
        eliteOnly: false
      },
      {
        value: "metaverse",
        label: "metaverse",
        eliteOnly: false
      },
      {
        value: "microcap",
        label: "micro-cap",
        eliteOnly: false
      },
      {
        value: "midcap",
        label: "mid-cap",
        eliteOnly: false
      },
      {
        value: "midlargecap",
        label: "mid-large-cap",
        eliteOnly: false
      },
      {
        value: "midstream",
        label: "midstream",
        eliteOnly: false
      },
      {
        value: "military",
        label: "military",
        eliteOnly: false
      },
      {
        value: "millennial",
        label: "millennial",
        eliteOnly: false
      },
      {
        value: "miners",
        label: "miners",
        eliteOnly: false
      },
      {
        value: "moderate",
        label: "moderate",
        eliteOnly: false
      },
      {
        value: "momentum",
        label: "momentum",
        eliteOnly: false
      },
      {
        value: "monopolies",
        label: "monopolies",
        eliteOnly: false
      },
      {
        value: "multiasset",
        label: "multi-asset",
        eliteOnly: false
      },
      {
        value: "multifactor",
        label: "multi-factor",
        eliteOnly: false
      },
      {
        value: "multisector",
        label: "multi-sector",
        eliteOnly: false
      },
      {
        value: "municipalbonds",
        label: "municipal-bonds",
        eliteOnly: false
      },
      {
        value: "music",
        label: "music",
        eliteOnly: false
      },
      {
        value: "naturalgas",
        label: "natural-gas",
        eliteOnly: false
      },
      {
        value: "naturalresources",
        label: "natural-resources",
        eliteOnly: false
      },
      {
        value: "network",
        label: "network",
        eliteOnly: false
      },
      {
        value: "nextgen",
        label: "next-gen",
        eliteOnly: false
      },
      {
        value: "nickel",
        label: "nickel",
        eliteOnly: false
      },
      {
        value: "nonesg",
        label: "non-ESG",
        eliteOnly: false
      },
      {
        value: "nuclearenergy",
        label: "nuclear-energy",
        eliteOnly: false
      },
      {
        value: "oil",
        label: "oil",
        eliteOnly: false
      },
      {
        value: "oilgasexpprod",
        label: "oil-gas-exp-prod",
        eliteOnly: false
      },
      {
        value: "oilgasservices",
        label: "oil-gas-services",
        eliteOnly: false
      },
      {
        value: "onlinestores",
        label: "online-stores",
        eliteOnly: false
      },
      {
        value: "options",
        label: "options",
        eliteOnly: false
      },
      {
        value: "palladium",
        label: "palladium",
        eliteOnly: false
      },
      {
        value: "patents",
        label: "patents",
        eliteOnly: false
      },
      {
        value: "petcare",
        label: "pet-care",
        eliteOnly: false
      },
      {
        value: "pharmaceutical",
        label: "pharmaceutical",
        eliteOnly: false
      },
      {
        value: "philippines",
        label: "philippines",
        eliteOnly: false
      },
      {
        value: "physical",
        label: "physical",
        eliteOnly: false
      },
      {
        value: "pipelines",
        label: "pipelines",
        eliteOnly: false
      },
      {
        value: "platinum",
        label: "platinum",
        eliteOnly: false
      },
      {
        value: "politics",
        label: "politics",
        eliteOnly: false
      },
      {
        value: "preciousmetals",
        label: "precious-metals",
        eliteOnly: false
      },
      {
        value: "preferred",
        label: "preferred",
        eliteOnly: false
      },
      {
        value: "preferredsecurities",
        label: "preferred-securities",
        eliteOnly: false
      },
      {
        value: "privatecredit",
        label: "private-credit",
        eliteOnly: false
      },
      {
        value: "privateequity",
        label: "private-equity",
        eliteOnly: false
      },
      {
        value: "putwrite",
        label: "put-write",
        eliteOnly: false
      },
      {
        value: "quality",
        label: "quality",
        eliteOnly: false
      },
      {
        value: "quantitative",
        label: "quantitative",
        eliteOnly: false
      },
      {
        value: "quantumcomputing",
        label: "quantum-computing",
        eliteOnly: false
      },
      {
        value: "rareearth",
        label: "rare-earth",
        eliteOnly: false
      },
      {
        value: "realassets",
        label: "real-assets",
        eliteOnly: false
      },
      {
        value: "realestate",
        label: "real-estate",
        eliteOnly: false
      },
      {
        value: "regionalbanks",
        label: "regional-banks",
        eliteOnly: false
      },
      {
        value: "relativestrength",
        label: "relative-strength",
        eliteOnly: false
      },
      {
        value: "renewableenergy",
        label: "renewable-energy",
        eliteOnly: false
      },
      {
        value: "republicans",
        label: "republicans",
        eliteOnly: false
      },
      {
        value: "responsible",
        label: "responsible",
        eliteOnly: false
      },
      {
        value: "restaurant",
        label: "restaurant",
        eliteOnly: false
      },
      {
        value: "retail",
        label: "retail",
        eliteOnly: false
      },
      {
        value: "retailstores",
        label: "retail-stores",
        eliteOnly: false
      },
      {
        value: "revenue",
        label: "revenue",
        eliteOnly: false
      },
      {
        value: "ripple",
        label: "ripple",
        eliteOnly: false
      },
      {
        value: "risingrates",
        label: "rising-rates",
        eliteOnly: false
      },
      {
        value: "robotics",
        label: "robotics",
        eliteOnly: false
      },
      {
        value: "sectorrotation",
        label: "sector-rotation",
        eliteOnly: false
      },
      {
        value: "semiconductors",
        label: "semiconductors",
        eliteOnly: false
      },
      {
        value: "seniorloans",
        label: "senior-loans",
        eliteOnly: false
      },
      {
        value: "shariacompliant",
        label: "sharia-compliant",
        eliteOnly: false
      },
      {
        value: "shipping",
        label: "shipping",
        eliteOnly: false
      },
      {
        value: "short",
        label: "short",
        eliteOnly: false
      },
      {
        value: "silver",
        label: "silver",
        eliteOnly: false
      },
      {
        value: "silverminers",
        label: "silver-miners",
        eliteOnly: false
      },
      {
        value: "singleasset",
        label: "single-asset",
        eliteOnly: false
      },
      {
        value: "smallcap",
        label: "small-cap",
        eliteOnly: false
      },
      {
        value: "smallmidcap",
        label: "small-mid-cap",
        eliteOnly: false
      },
      {
        value: "smartgrid",
        label: "smart-grid",
        eliteOnly: false
      },
      {
        value: "smartmobility",
        label: "smart-mobility",
        eliteOnly: false
      },
      {
        value: "social",
        label: "social",
        eliteOnly: false
      },
      {
        value: "socialmedia",
        label: "social-media",
        eliteOnly: false
      },
      {
        value: "software",
        label: "software",
        eliteOnly: false
      },
      {
        value: "solana",
        label: "solana",
        eliteOnly: false
      },
      {
        value: "solar",
        label: "solar",
        eliteOnly: false
      },
      {
        value: "soybean",
        label: "soybean",
        eliteOnly: false
      },
      {
        value: "spaceexploration",
        label: "space-exploration",
        eliteOnly: false
      },
      {
        value: "spinoff",
        label: "spin-off",
        eliteOnly: false
      },
      {
        value: "steel",
        label: "steel",
        eliteOnly: false
      },
      {
        value: "sugar",
        label: "sugar",
        eliteOnly: false
      },
      {
        value: "sui",
        label: "sui",
        eliteOnly: false
      },
      {
        value: "sukuk",
        label: "sukuk",
        eliteOnly: false
      },
      {
        value: "sustainability",
        label: "sustainability",
        eliteOnly: false
      },
      {
        value: "tactical",
        label: "tactical",
        eliteOnly: false
      },
      {
        value: "targetdrawdown",
        label: "target-drawdown",
        eliteOnly: false
      },
      {
        value: "technology",
        label: "technology",
        eliteOnly: false
      },
      {
        value: "timber",
        label: "timber",
        eliteOnly: false
      },
      {
        value: "transportation",
        label: "transportation",
        eliteOnly: false
      },
      {
        value: "travel",
        label: "travel",
        eliteOnly: false
      },
      {
        value: "treasuries",
        label: "treasuries",
        eliteOnly: false
      },
      {
        value: "upsidecap",
        label: "upside-cap",
        eliteOnly: false
      },
      {
        value: "upstream",
        label: "upstream",
        eliteOnly: false
      },
      {
        value: "uranium",
        label: "uranium",
        eliteOnly: false
      },
      {
        value: "uraniumminers",
        label: "uranium-miners",
        eliteOnly: false
      },
      {
        value: "utilities",
        label: "utilities",
        eliteOnly: false
      },
      {
        value: "value",
        label: "value",
        eliteOnly: false
      },
      {
        value: "variablerate",
        label: "variable-rate",
        eliteOnly: false
      },
      {
        value: "vegan",
        label: "vegan",
        eliteOnly: false
      },
      {
        value: "vix",
        label: "vix",
        eliteOnly: false
      },
      {
        value: "volatility",
        label: "volatility",
        eliteOnly: false
      },
      {
        value: "volatilityindex",
        label: "volatility-index",
        eliteOnly: false
      },
      {
        value: "volatilityweight",
        label: "volatility-weight",
        eliteOnly: false
      },
      {
        value: "water",
        label: "water",
        eliteOnly: false
      },
      {
        value: "wheat",
        label: "wheat",
        eliteOnly: false
      },
      {
        value: "wind",
        label: "wind",
        eliteOnly: false
      },
      {
        value: "wood",
        label: "wood",
        eliteOnly: false
      },
      {
        value: "zerocoupon",
        label: "zero-coupon",
        eliteOnly: false
      },
      {
        value: "custom_subscription",
        label: "Custom (Elite only)",
        eliteOnly: true
      }
    ]
  },
  exchange: {
    key: "exchange",
    label: "Exchange",
    dataFilter: "exch",
    groups: [
      "descriptive",
      "all"
    ],
    options: [
      {
        value: "",
        label: "Any",
        eliteOnly: false
      },
      {
        value: "amex",
        label: "AMEX",
        eliteOnly: false
      },
      {
        value: "cboe",
        label: "CBOE",
        eliteOnly: false
      },
      {
        value: "nasd",
        label: "NASDAQ",
        eliteOnly: false
      },
      {
        value: "nyse",
        label: "NYSE",
        eliteOnly: false
      },
      {
        value: "custom_subscription",
        label: "Custom (Elite only)",
        eliteOnly: true
      }
    ]
  },
  fa_curratio: {
    key: "fa_curratio",
    label: "Current Ratio",
    dataFilter: "fa_curratio",
    groups: [
      "fundamental",
      "all"
    ],
    options: [
      {
        value: "",
        label: "Any",
        eliteOnly: false
      },
      {
        value: "high",
        label: "High (>3)",
        eliteOnly: false
      },
      {
        value: "low",
        label: "Low (<1)",
        eliteOnly: false
      },
      {
        value: "o0.5",
        label: "Over 0.5",
        eliteOnly: false
      },
      {
        value: "o1",
        label: "Over 1",
        eliteOnly: false
      },
      {
        value: "o1.5",
        label: "Over 1.5",
        eliteOnly: false
      },
      {
        value: "o10",
        label: "Over 10",
        eliteOnly: false
      },
      {
        value: "o2",
        label: "Over 2",
        eliteOnly: false
      },
      {
        value: "o3",
        label: "Over 3",
        eliteOnly: false
      },
      {
        value: "o4",
        label: "Over 4",
        eliteOnly: false
      },
      {
        value: "o5",
        label: "Over 5",
        eliteOnly: false
      },
      {
        value: "u0.5",
        label: "Under 0.5",
        eliteOnly: false
      },
      {
        value: "u1",
        label: "Under 1",
        eliteOnly: false
      },
      {
        value: "custom_subscription",
        label: "Custom (Elite only)",
        eliteOnly: true
      }
    ]
  },
  fa_debteq: {
    key: "fa_debteq",
    label: "Debt/Equity",
    dataFilter: "fa_debteq",
    groups: [
      "fundamental",
      "all"
    ],
    options: [
      {
        value: "",
        label: "Any",
        eliteOnly: false
      },
      {
        value: "high",
        label: "High (>0.5)",
        eliteOnly: false
      },
      {
        value: "low",
        label: "Low (<0.1)",
        eliteOnly: false
      },
      {
        value: "o0.1",
        label: "Over 0.1",
        eliteOnly: false
      },
      {
        value: "o0.2",
        label: "Over 0.2",
        eliteOnly: false
      },
      {
        value: "o0.3",
        label: "Over 0.3",
        eliteOnly: false
      },
      {
        value: "o0.4",
        label: "Over 0.4",
        eliteOnly: false
      },
      {
        value: "o0.5",
        label: "Over 0.5",
        eliteOnly: false
      },
      {
        value: "o0.6",
        label: "Over 0.6",
        eliteOnly: false
      },
      {
        value: "o0.7",
        label: "Over 0.7",
        eliteOnly: false
      },
      {
        value: "o0.8",
        label: "Over 0.8",
        eliteOnly: false
      },
      {
        value: "o0.9",
        label: "Over 0.9",
        eliteOnly: false
      },
      {
        value: "o1",
        label: "Over 1",
        eliteOnly: false
      },
      {
        value: "u0.1",
        label: "Under 0.1",
        eliteOnly: false
      },
      {
        value: "u0.2",
        label: "Under 0.2",
        eliteOnly: false
      },
      {
        value: "u0.3",
        label: "Under 0.3",
        eliteOnly: false
      },
      {
        value: "u0.4",
        label: "Under 0.4",
        eliteOnly: false
      },
      {
        value: "u0.5",
        label: "Under 0.5",
        eliteOnly: false
      },
      {
        value: "u0.6",
        label: "Under 0.6",
        eliteOnly: false
      },
      {
        value: "u0.7",
        label: "Under 0.7",
        eliteOnly: false
      },
      {
        value: "u0.8",
        label: "Under 0.8",
        eliteOnly: false
      },
      {
        value: "u0.9",
        label: "Under 0.9",
        eliteOnly: false
      },
      {
        value: "u1",
        label: "Under 1",
        eliteOnly: false
      },
      {
        value: "custom_subscription",
        label: "Custom (Elite only)",
        eliteOnly: true
      }
    ]
  },
  fa_divgrowth: {
    key: "fa_divgrowth",
    label: "Dividend Growth",
    dataFilter: "fa_divgrowth",
    groups: [
      "fundamental",
      "all"
    ],
    options: [
      {
        value: "",
        label: "Any",
        eliteOnly: false
      },
      {
        value: "1yo10",
        label: "1 Year Over 10%",
        eliteOnly: false
      },
      {
        value: "1yo15",
        label: "1 Year Over 15%",
        eliteOnly: false
      },
      {
        value: "1yo20",
        label: "1 Year Over 20%",
        eliteOnly: false
      },
      {
        value: "1yo25",
        label: "1 Year Over 25%",
        eliteOnly: false
      },
      {
        value: "1yo30",
        label: "1 Year Over 30%",
        eliteOnly: false
      },
      {
        value: "1yo5",
        label: "1 Year Over 5%",
        eliteOnly: false
      },
      {
        value: "1ypos",
        label: "1 Year Positive",
        eliteOnly: false
      },
      {
        value: "3yo10",
        label: "3 Years Over 10%",
        eliteOnly: false
      },
      {
        value: "3yo15",
        label: "3 Years Over 15%",
        eliteOnly: false
      },
      {
        value: "3yo20",
        label: "3 Years Over 20%",
        eliteOnly: false
      },
      {
        value: "3yo25",
        label: "3 Years Over 25%",
        eliteOnly: false
      },
      {
        value: "3yo30",
        label: "3 Years Over 30%",
        eliteOnly: false
      },
      {
        value: "3yo5",
        label: "3 Years Over 5%",
        eliteOnly: false
      },
      {
        value: "3ypos",
        label: "3 Years Positive",
        eliteOnly: false
      },
      {
        value: "5yo10",
        label: "5 Years Over 10%",
        eliteOnly: false
      },
      {
        value: "5yo15",
        label: "5 Years Over 15%",
        eliteOnly: false
      },
      {
        value: "5yo20",
        label: "5 Years Over 20%",
        eliteOnly: false
      },
      {
        value: "5yo25",
        label: "5 Years Over 25%",
        eliteOnly: false
      },
      {
        value: "5yo30",
        label: "5 Years Over 30%",
        eliteOnly: false
      },
      {
        value: "5yo5",
        label: "5 Years Over 5%",
        eliteOnly: false
      },
      {
        value: "5ypos",
        label: "5 Years Positive",
        eliteOnly: false
      },
      {
        value: "cy1",
        label: "Growing 1+ Year",
        eliteOnly: false
      },
      {
        value: "cy2",
        label: "Growing 2+ Years",
        eliteOnly: false
      },
      {
        value: "cy3",
        label: "Growing 3+ Years",
        eliteOnly: false
      },
      {
        value: "cy4",
        label: "Growing 4+ Years",
        eliteOnly: false
      },
      {
        value: "cy5",
        label: "Growing 5+ Years",
        eliteOnly: false
      },
      {
        value: "cy6",
        label: "Growing 6+ Years",
        eliteOnly: false
      },
      {
        value: "cy7",
        label: "Growing 7+ Years",
        eliteOnly: false
      },
      {
        value: "cy8",
        label: "Growing 8+ Years",
        eliteOnly: false
      },
      {
        value: "cy9",
        label: "Growing 9+ Years",
        eliteOnly: false
      },
      {
        value: "custom_subscription",
        label: "Custom (Elite only)",
        eliteOnly: true
      }
    ]
  },
  fa_eps3years: {
    key: "fa_eps3years",
    label: "EPS Growth Past 3 Years",
    dataFilter: "fa_eps3years",
    groups: [
      "fundamental",
      "all"
    ],
    options: [
      {
        value: "",
        label: "Any",
        eliteOnly: false
      },
      {
        value: "high",
        label: "High (>25%)",
        eliteOnly: false
      },
      {
        value: "neg",
        label: "Negative (<0%)",
        eliteOnly: false
      },
      {
        value: "o10",
        label: "Over 10%",
        eliteOnly: false
      },
      {
        value: "o15",
        label: "Over 15%",
        eliteOnly: false
      },
      {
        value: "o20",
        label: "Over 20%",
        eliteOnly: false
      },
      {
        value: "o25",
        label: "Over 25%",
        eliteOnly: false
      },
      {
        value: "o30",
        label: "Over 30%",
        eliteOnly: false
      },
      {
        value: "o5",
        label: "Over 5%",
        eliteOnly: false
      },
      {
        value: "pos",
        label: "Positive (>0%)",
        eliteOnly: false
      },
      {
        value: "poslow",
        label: "Positive Low (0-10%)",
        eliteOnly: false
      },
      {
        value: "u10",
        label: "Under 10%",
        eliteOnly: false
      },
      {
        value: "u15",
        label: "Under 15%",
        eliteOnly: false
      },
      {
        value: "u20",
        label: "Under 20%",
        eliteOnly: false
      },
      {
        value: "u25",
        label: "Under 25%",
        eliteOnly: false
      },
      {
        value: "u30",
        label: "Under 30%",
        eliteOnly: false
      },
      {
        value: "u5",
        label: "Under 5%",
        eliteOnly: false
      },
      {
        value: "custom_subscription",
        label: "Custom (Elite only)",
        eliteOnly: true
      }
    ]
  },
  fa_eps5years: {
    key: "fa_eps5years",
    label: "EPS Growth Past 5 Years",
    dataFilter: "fa_eps5years",
    groups: [
      "fundamental",
      "all"
    ],
    options: [
      {
        value: "",
        label: "Any",
        eliteOnly: false
      },
      {
        value: "high",
        label: "High (>25%)",
        eliteOnly: false
      },
      {
        value: "neg",
        label: "Negative (<0%)",
        eliteOnly: false
      },
      {
        value: "o10",
        label: "Over 10%",
        eliteOnly: false
      },
      {
        value: "o15",
        label: "Over 15%",
        eliteOnly: false
      },
      {
        value: "o20",
        label: "Over 20%",
        eliteOnly: false
      },
      {
        value: "o25",
        label: "Over 25%",
        eliteOnly: false
      },
      {
        value: "o30",
        label: "Over 30%",
        eliteOnly: false
      },
      {
        value: "o5",
        label: "Over 5%",
        eliteOnly: false
      },
      {
        value: "pos",
        label: "Positive (>0%)",
        eliteOnly: false
      },
      {
        value: "poslow",
        label: "Positive Low (0-10%)",
        eliteOnly: false
      },
      {
        value: "u10",
        label: "Under 10%",
        eliteOnly: false
      },
      {
        value: "u15",
        label: "Under 15%",
        eliteOnly: false
      },
      {
        value: "u20",
        label: "Under 20%",
        eliteOnly: false
      },
      {
        value: "u25",
        label: "Under 25%",
        eliteOnly: false
      },
      {
        value: "u30",
        label: "Under 30%",
        eliteOnly: false
      },
      {
        value: "u5",
        label: "Under 5%",
        eliteOnly: false
      },
      {
        value: "custom_subscription",
        label: "Custom (Elite only)",
        eliteOnly: true
      }
    ]
  },
  fa_epsqoq: {
    key: "fa_epsqoq",
    label: "EPS Growth Qtr Over Qtr",
    dataFilter: "fa_epsqoq",
    groups: [
      "fundamental",
      "all"
    ],
    options: [
      {
        value: "",
        label: "Any",
        eliteOnly: false
      },
      {
        value: "high",
        label: "High (>25%)",
        eliteOnly: false
      },
      {
        value: "neg",
        label: "Negative (<0%)",
        eliteOnly: false
      },
      {
        value: "o10",
        label: "Over 10%",
        eliteOnly: false
      },
      {
        value: "o15",
        label: "Over 15%",
        eliteOnly: false
      },
      {
        value: "o20",
        label: "Over 20%",
        eliteOnly: false
      },
      {
        value: "o25",
        label: "Over 25%",
        eliteOnly: false
      },
      {
        value: "o30",
        label: "Over 30%",
        eliteOnly: false
      },
      {
        value: "o5",
        label: "Over 5%",
        eliteOnly: false
      },
      {
        value: "pos",
        label: "Positive (>0%)",
        eliteOnly: false
      },
      {
        value: "poslow",
        label: "Positive Low (0-10%)",
        eliteOnly: false
      },
      {
        value: "u10",
        label: "Under 10%",
        eliteOnly: false
      },
      {
        value: "u15",
        label: "Under 15%",
        eliteOnly: false
      },
      {
        value: "u20",
        label: "Under 20%",
        eliteOnly: false
      },
      {
        value: "u25",
        label: "Under 25%",
        eliteOnly: false
      },
      {
        value: "u30",
        label: "Under 30%",
        eliteOnly: false
      },
      {
        value: "u5",
        label: "Under 5%",
        eliteOnly: false
      },
      {
        value: "custom_subscription",
        label: "Custom (Elite only)",
        eliteOnly: true
      }
    ]
  },
  fa_epsrev: {
    key: "fa_epsrev",
    label: "Earnings & Revenue Surprise",
    dataFilter: "fa_epsrev",
    groups: [
      "fundamental",
      "all"
    ],
    options: [
      {
        value: "",
        label: "Any",
        eliteOnly: false
      },
      {
        value: "bm",
        label: "Both met (0%)",
        eliteOnly: false
      },
      {
        value: "bn",
        label: "Both negative (<0%)",
        eliteOnly: false
      },
      {
        value: "bp",
        label: "Both positive (>0%)",
        eliteOnly: false
      },
      {
        value: "em",
        label: "Met (0%)",
        eliteOnly: false
      },
      {
        value: "rm",
        label: "Met (0%)",
        eliteOnly: false
      },
      {
        value: "en",
        label: "Negative (<0%)",
        eliteOnly: false
      },
      {
        value: "rn",
        label: "Negative (<0%)",
        eliteOnly: false
      },
      {
        value: "eo10",
        label: "Over 10%",
        eliteOnly: false
      },
      {
        value: "ro10",
        label: "Over 10%",
        eliteOnly: false
      },
      {
        value: "eo100",
        label: "Over 100%",
        eliteOnly: false
      },
      {
        value: "ro100",
        label: "Over 100%",
        eliteOnly: false
      },
      {
        value: "eo20",
        label: "Over 20%",
        eliteOnly: false
      },
      {
        value: "ro20",
        label: "Over 20%",
        eliteOnly: false
      },
      {
        value: "eo200",
        label: "Over 200%",
        eliteOnly: false
      },
      {
        value: "ro200",
        label: "Over 200%",
        eliteOnly: false
      },
      {
        value: "eo30",
        label: "Over 30%",
        eliteOnly: false
      },
      {
        value: "ro30",
        label: "Over 30%",
        eliteOnly: false
      },
      {
        value: "eo40",
        label: "Over 40%",
        eliteOnly: false
      },
      {
        value: "ro40",
        label: "Over 40%",
        eliteOnly: false
      },
      {
        value: "eo5",
        label: "Over 5%",
        eliteOnly: false
      },
      {
        value: "ro5",
        label: "Over 5%",
        eliteOnly: false
      },
      {
        value: "eo50",
        label: "Over 50%",
        eliteOnly: false
      },
      {
        value: "ro50",
        label: "Over 50%",
        eliteOnly: false
      },
      {
        value: "eo60",
        label: "Over 60%",
        eliteOnly: false
      },
      {
        value: "ro60",
        label: "Over 60%",
        eliteOnly: false
      },
      {
        value: "eo70",
        label: "Over 70%",
        eliteOnly: false
      },
      {
        value: "ro70",
        label: "Over 70%",
        eliteOnly: false
      },
      {
        value: "eo80",
        label: "Over 80%",
        eliteOnly: false
      },
      {
        value: "ro80",
        label: "Over 80%",
        eliteOnly: false
      },
      {
        value: "eo90",
        label: "Over 90%",
        eliteOnly: false
      },
      {
        value: "ro90",
        label: "Over 90%",
        eliteOnly: false
      },
      {
        value: "ep",
        label: "Positive (>0%)",
        eliteOnly: false
      },
      {
        value: "rp",
        label: "Positive (>0%)",
        eliteOnly: false
      },
      {
        value: "eu10",
        label: "Under -10%",
        eliteOnly: false
      },
      {
        value: "ru10",
        label: "Under -10%",
        eliteOnly: false
      },
      {
        value: "eu100",
        label: "Under -100%",
        eliteOnly: false
      },
      {
        value: "ru100",
        label: "Under -100%",
        eliteOnly: false
      },
      {
        value: "eu20",
        label: "Under -20%",
        eliteOnly: false
      },
      {
        value: "ru20",
        label: "Under -20%",
        eliteOnly: false
      },
      {
        value: "eu30",
        label: "Under -30%",
        eliteOnly: false
      },
      {
        value: "ru30",
        label: "Under -30%",
        eliteOnly: false
      },
      {
        value: "eu40",
        label: "Under -40%",
        eliteOnly: false
      },
      {
        value: "ru40",
        label: "Under -40%",
        eliteOnly: false
      },
      {
        value: "eu5",
        label: "Under -5%",
        eliteOnly: false
      },
      {
        value: "ru5",
        label: "Under -5%",
        eliteOnly: false
      },
      {
        value: "eu50",
        label: "Under -50%",
        eliteOnly: false
      },
      {
        value: "ru50",
        label: "Under -50%",
        eliteOnly: false
      },
      {
        value: "custom_subscription",
        label: "Custom (Elite only)",
        eliteOnly: true
      }
    ]
  },
  fa_epsyoy: {
    key: "fa_epsyoy",
    label: "EPS Growth This Year",
    dataFilter: "fa_epsyoy",
    groups: [
      "fundamental",
      "all"
    ],
    options: [
      {
        value: "",
        label: "Any",
        eliteOnly: false
      },
      {
        value: "high",
        label: "High (>25%)",
        eliteOnly: false
      },
      {
        value: "neg",
        label: "Negative (<0%)",
        eliteOnly: false
      },
      {
        value: "o10",
        label: "Over 10%",
        eliteOnly: false
      },
      {
        value: "o15",
        label: "Over 15%",
        eliteOnly: false
      },
      {
        value: "o20",
        label: "Over 20%",
        eliteOnly: false
      },
      {
        value: "o25",
        label: "Over 25%",
        eliteOnly: false
      },
      {
        value: "o30",
        label: "Over 30%",
        eliteOnly: false
      },
      {
        value: "o5",
        label: "Over 5%",
        eliteOnly: false
      },
      {
        value: "pos",
        label: "Positive (>0%)",
        eliteOnly: false
      },
      {
        value: "poslow",
        label: "Positive Low (0-10%)",
        eliteOnly: false
      },
      {
        value: "u10",
        label: "Under 10%",
        eliteOnly: false
      },
      {
        value: "u15",
        label: "Under 15%",
        eliteOnly: false
      },
      {
        value: "u20",
        label: "Under 20%",
        eliteOnly: false
      },
      {
        value: "u25",
        label: "Under 25%",
        eliteOnly: false
      },
      {
        value: "u30",
        label: "Under 30%",
        eliteOnly: false
      },
      {
        value: "u5",
        label: "Under 5%",
        eliteOnly: false
      },
      {
        value: "custom_subscription",
        label: "Custom (Elite only)",
        eliteOnly: true
      }
    ]
  },
  fa_epsyoy1: {
    key: "fa_epsyoy1",
    label: "EPS Growth Next Year",
    dataFilter: "fa_epsyoy1",
    groups: [
      "fundamental",
      "all"
    ],
    options: [
      {
        value: "",
        label: "Any",
        eliteOnly: false
      },
      {
        value: "high",
        label: "High (>25%)",
        eliteOnly: false
      },
      {
        value: "neg",
        label: "Negative (<0%)",
        eliteOnly: false
      },
      {
        value: "o10",
        label: "Over 10%",
        eliteOnly: false
      },
      {
        value: "o15",
        label: "Over 15%",
        eliteOnly: false
      },
      {
        value: "o20",
        label: "Over 20%",
        eliteOnly: false
      },
      {
        value: "o25",
        label: "Over 25%",
        eliteOnly: false
      },
      {
        value: "o30",
        label: "Over 30%",
        eliteOnly: false
      },
      {
        value: "o5",
        label: "Over 5%",
        eliteOnly: false
      },
      {
        value: "pos",
        label: "Positive (>0%)",
        eliteOnly: false
      },
      {
        value: "poslow",
        label: "Positive Low (0-10%)",
        eliteOnly: false
      },
      {
        value: "u10",
        label: "Under 10%",
        eliteOnly: false
      },
      {
        value: "u15",
        label: "Under 15%",
        eliteOnly: false
      },
      {
        value: "u20",
        label: "Under 20%",
        eliteOnly: false
      },
      {
        value: "u25",
        label: "Under 25%",
        eliteOnly: false
      },
      {
        value: "u30",
        label: "Under 30%",
        eliteOnly: false
      },
      {
        value: "u5",
        label: "Under 5%",
        eliteOnly: false
      },
      {
        value: "custom_subscription",
        label: "Custom (Elite only)",
        eliteOnly: true
      }
    ]
  },
  fa_epsyoyttm: {
    key: "fa_epsyoyttm",
    label: "EPS Growth TTM",
    dataFilter: "fa_epsyoyttm",
    groups: [
      "fundamental",
      "all"
    ],
    options: [
      {
        value: "",
        label: "Any",
        eliteOnly: false
      },
      {
        value: "high",
        label: "High (>25%)",
        eliteOnly: false
      },
      {
        value: "neg",
        label: "Negative (<0%)",
        eliteOnly: false
      },
      {
        value: "o10",
        label: "Over 10%",
        eliteOnly: false
      },
      {
        value: "o15",
        label: "Over 15%",
        eliteOnly: false
      },
      {
        value: "o20",
        label: "Over 20%",
        eliteOnly: false
      },
      {
        value: "o25",
        label: "Over 25%",
        eliteOnly: false
      },
      {
        value: "o30",
        label: "Over 30%",
        eliteOnly: false
      },
      {
        value: "o5",
        label: "Over 5%",
        eliteOnly: false
      },
      {
        value: "pos",
        label: "Positive (>0%)",
        eliteOnly: false
      },
      {
        value: "poslow",
        label: "Positive Low (0-10%)",
        eliteOnly: false
      },
      {
        value: "u10",
        label: "Under 10%",
        eliteOnly: false
      },
      {
        value: "u15",
        label: "Under 15%",
        eliteOnly: false
      },
      {
        value: "u20",
        label: "Under 20%",
        eliteOnly: false
      },
      {
        value: "u25",
        label: "Under 25%",
        eliteOnly: false
      },
      {
        value: "u30",
        label: "Under 30%",
        eliteOnly: false
      },
      {
        value: "u5",
        label: "Under 5%",
        eliteOnly: false
      },
      {
        value: "custom_subscription",
        label: "Custom (Elite only)",
        eliteOnly: true
      }
    ]
  },
  fa_estltgrowth: {
    key: "fa_estltgrowth",
    label: "EPS Growth Next 5 Years",
    dataFilter: "fa_estltgrowth",
    groups: [
      "fundamental",
      "all"
    ],
    options: [
      {
        value: "",
        label: "Any",
        eliteOnly: false
      },
      {
        value: "high",
        label: "High (>25%)",
        eliteOnly: false
      },
      {
        value: "neg",
        label: "Negative (<0%)",
        eliteOnly: false
      },
      {
        value: "o10",
        label: "Over 10%",
        eliteOnly: false
      },
      {
        value: "o15",
        label: "Over 15%",
        eliteOnly: false
      },
      {
        value: "o20",
        label: "Over 20%",
        eliteOnly: false
      },
      {
        value: "o25",
        label: "Over 25%",
        eliteOnly: false
      },
      {
        value: "o30",
        label: "Over 30%",
        eliteOnly: false
      },
      {
        value: "o5",
        label: "Over 5%",
        eliteOnly: false
      },
      {
        value: "pos",
        label: "Positive (>0%)",
        eliteOnly: false
      },
      {
        value: "poslow",
        label: "Positive Low (<10%)",
        eliteOnly: false
      },
      {
        value: "u10",
        label: "Under 10%",
        eliteOnly: false
      },
      {
        value: "u15",
        label: "Under 15%",
        eliteOnly: false
      },
      {
        value: "u20",
        label: "Under 20%",
        eliteOnly: false
      },
      {
        value: "u25",
        label: "Under 25%",
        eliteOnly: false
      },
      {
        value: "u30",
        label: "Under 30%",
        eliteOnly: false
      },
      {
        value: "u5",
        label: "Under 5%",
        eliteOnly: false
      },
      {
        value: "custom_subscription",
        label: "Custom (Elite only)",
        eliteOnly: true
      }
    ]
  },
  fa_evebitda: {
    key: "fa_evebitda",
    label: "EV/EBITDA",
    dataFilter: "fa_evebitda",
    groups: [
      "fundamental",
      "all"
    ],
    options: [
      {
        value: "",
        label: "Any",
        eliteOnly: false
      },
      {
        value: "high",
        label: "High (>50)",
        eliteOnly: false
      },
      {
        value: "low",
        label: "Low (<15)",
        eliteOnly: false
      },
      {
        value: "negative",
        label: "Negative (<0)",
        eliteOnly: false
      },
      {
        value: "o10",
        label: "Over 10",
        eliteOnly: false
      },
      {
        value: "o15",
        label: "Over 15",
        eliteOnly: false
      },
      {
        value: "o20",
        label: "Over 20",
        eliteOnly: false
      },
      {
        value: "o25",
        label: "Over 25",
        eliteOnly: false
      },
      {
        value: "o30",
        label: "Over 30",
        eliteOnly: false
      },
      {
        value: "o35",
        label: "Over 35",
        eliteOnly: false
      },
      {
        value: "o40",
        label: "Over 40",
        eliteOnly: false
      },
      {
        value: "o45",
        label: "Over 45",
        eliteOnly: false
      },
      {
        value: "o5",
        label: "Over 5",
        eliteOnly: false
      },
      {
        value: "o50",
        label: "Over 50",
        eliteOnly: false
      },
      {
        value: "profitable",
        label: "Profitable (>0)",
        eliteOnly: false
      },
      {
        value: "u10",
        label: "Under 10",
        eliteOnly: false
      },
      {
        value: "u15",
        label: "Under 15",
        eliteOnly: false
      },
      {
        value: "u20",
        label: "Under 20",
        eliteOnly: false
      },
      {
        value: "u25",
        label: "Under 25",
        eliteOnly: false
      },
      {
        value: "u30",
        label: "Under 30",
        eliteOnly: false
      },
      {
        value: "u35",
        label: "Under 35",
        eliteOnly: false
      },
      {
        value: "u40",
        label: "Under 40",
        eliteOnly: false
      },
      {
        value: "u45",
        label: "Under 45",
        eliteOnly: false
      },
      {
        value: "u5",
        label: "Under 5",
        eliteOnly: false
      },
      {
        value: "u50",
        label: "Under 50",
        eliteOnly: false
      },
      {
        value: "custom_subscription",
        label: "Custom (Elite only)",
        eliteOnly: true
      }
    ]
  },
  fa_evsales: {
    key: "fa_evsales",
    label: "EV/Sales",
    dataFilter: "fa_evsales",
    groups: [
      "fundamental",
      "all"
    ],
    options: [
      {
        value: "",
        label: "Any",
        eliteOnly: false
      },
      {
        value: "high",
        label: "High (>10)",
        eliteOnly: false
      },
      {
        value: "low",
        label: "Low (<1)",
        eliteOnly: false
      },
      {
        value: "negative",
        label: "Negative (<0)",
        eliteOnly: false
      },
      {
        value: "o1",
        label: "Over 1",
        eliteOnly: false
      },
      {
        value: "o10",
        label: "Over 10",
        eliteOnly: false
      },
      {
        value: "o2",
        label: "Over 2",
        eliteOnly: false
      },
      {
        value: "o3",
        label: "Over 3",
        eliteOnly: false
      },
      {
        value: "o4",
        label: "Over 4",
        eliteOnly: false
      },
      {
        value: "o5",
        label: "Over 5",
        eliteOnly: false
      },
      {
        value: "o6",
        label: "Over 6",
        eliteOnly: false
      },
      {
        value: "o7",
        label: "Over 7",
        eliteOnly: false
      },
      {
        value: "o8",
        label: "Over 8",
        eliteOnly: false
      },
      {
        value: "o9",
        label: "Over 9",
        eliteOnly: false
      },
      {
        value: "positive",
        label: "Positive (>0)",
        eliteOnly: false
      },
      {
        value: "u1",
        label: "Under 1",
        eliteOnly: false
      },
      {
        value: "u10",
        label: "Under 10",
        eliteOnly: false
      },
      {
        value: "u2",
        label: "Under 2",
        eliteOnly: false
      },
      {
        value: "u3",
        label: "Under 3",
        eliteOnly: false
      },
      {
        value: "u4",
        label: "Under 4",
        eliteOnly: false
      },
      {
        value: "u5",
        label: "Under 5",
        eliteOnly: false
      },
      {
        value: "u6",
        label: "Under 6",
        eliteOnly: false
      },
      {
        value: "u7",
        label: "Under 7",
        eliteOnly: false
      },
      {
        value: "u8",
        label: "Under 8",
        eliteOnly: false
      },
      {
        value: "u9",
        label: "Under 9",
        eliteOnly: false
      },
      {
        value: "custom_subscription",
        label: "Custom (Elite only)",
        eliteOnly: true
      }
    ]
  },
  fa_fpe: {
    key: "fa_fpe",
    label: "Forward P/E",
    dataFilter: "fa_fpe",
    groups: [
      "fundamental",
      "all"
    ],
    options: [
      {
        value: "",
        label: "Any",
        eliteOnly: false
      },
      {
        value: "high",
        label: "High (>50)",
        eliteOnly: false
      },
      {
        value: "low",
        label: "Low (<15)",
        eliteOnly: false
      },
      {
        value: "o10",
        label: "Over 10",
        eliteOnly: false
      },
      {
        value: "o15",
        label: "Over 15",
        eliteOnly: false
      },
      {
        value: "o20",
        label: "Over 20",
        eliteOnly: false
      },
      {
        value: "o25",
        label: "Over 25",
        eliteOnly: false
      },
      {
        value: "o30",
        label: "Over 30",
        eliteOnly: false
      },
      {
        value: "o35",
        label: "Over 35",
        eliteOnly: false
      },
      {
        value: "o40",
        label: "Over 40",
        eliteOnly: false
      },
      {
        value: "o45",
        label: "Over 45",
        eliteOnly: false
      },
      {
        value: "o5",
        label: "Over 5",
        eliteOnly: false
      },
      {
        value: "o50",
        label: "Over 50",
        eliteOnly: false
      },
      {
        value: "profitable",
        label: "Profitable (>0)",
        eliteOnly: false
      },
      {
        value: "u10",
        label: "Under 10",
        eliteOnly: false
      },
      {
        value: "u15",
        label: "Under 15",
        eliteOnly: false
      },
      {
        value: "u20",
        label: "Under 20",
        eliteOnly: false
      },
      {
        value: "u25",
        label: "Under 25",
        eliteOnly: false
      },
      {
        value: "u30",
        label: "Under 30",
        eliteOnly: false
      },
      {
        value: "u35",
        label: "Under 35",
        eliteOnly: false
      },
      {
        value: "u40",
        label: "Under 40",
        eliteOnly: false
      },
      {
        value: "u45",
        label: "Under 45",
        eliteOnly: false
      },
      {
        value: "u5",
        label: "Under 5",
        eliteOnly: false
      },
      {
        value: "u50",
        label: "Under 50",
        eliteOnly: false
      },
      {
        value: "custom_subscription",
        label: "Custom (Elite only)",
        eliteOnly: true
      }
    ]
  },
  fa_grossmargin: {
    key: "fa_grossmargin",
    label: "Gross Margin",
    dataFilter: "fa_grossmargin",
    groups: [
      "fundamental",
      "all"
    ],
    options: [
      {
        value: "",
        label: "Any",
        eliteOnly: false
      },
      {
        value: "high",
        label: "High (>50%)",
        eliteOnly: false
      },
      {
        value: "neg",
        label: "Negative (<0%)",
        eliteOnly: false
      },
      {
        value: "o0",
        label: "Over 0%",
        eliteOnly: false
      },
      {
        value: "o10",
        label: "Over 10%",
        eliteOnly: false
      },
      {
        value: "o15",
        label: "Over 15%",
        eliteOnly: false
      },
      {
        value: "o20",
        label: "Over 20%",
        eliteOnly: false
      },
      {
        value: "o25",
        label: "Over 25%",
        eliteOnly: false
      },
      {
        value: "o30",
        label: "Over 30%",
        eliteOnly: false
      },
      {
        value: "o35",
        label: "Over 35%",
        eliteOnly: false
      },
      {
        value: "o40",
        label: "Over 40%",
        eliteOnly: false
      },
      {
        value: "o45",
        label: "Over 45%",
        eliteOnly: false
      },
      {
        value: "o5",
        label: "Over 5%",
        eliteOnly: false
      },
      {
        value: "o50",
        label: "Over 50%",
        eliteOnly: false
      },
      {
        value: "o60",
        label: "Over 60%",
        eliteOnly: false
      },
      {
        value: "o70",
        label: "Over 70%",
        eliteOnly: false
      },
      {
        value: "o80",
        label: "Over 80%",
        eliteOnly: false
      },
      {
        value: "o90",
        label: "Over 90%",
        eliteOnly: false
      },
      {
        value: "pos",
        label: "Positive (>0%)",
        eliteOnly: false
      },
      {
        value: "u-10",
        label: "Under -10%",
        eliteOnly: false
      },
      {
        value: "u-100",
        label: "Under -100%",
        eliteOnly: false
      },
      {
        value: "u-20",
        label: "Under -20%",
        eliteOnly: false
      },
      {
        value: "u-30",
        label: "Under -30%",
        eliteOnly: false
      },
      {
        value: "u-50",
        label: "Under -50%",
        eliteOnly: false
      },
      {
        value: "u-70",
        label: "Under -70%",
        eliteOnly: false
      },
      {
        value: "u0",
        label: "Under 0%",
        eliteOnly: false
      },
      {
        value: "u10",
        label: "Under 10%",
        eliteOnly: false
      },
      {
        value: "u15",
        label: "Under 15%",
        eliteOnly: false
      },
      {
        value: "u20",
        label: "Under 20%",
        eliteOnly: false
      },
      {
        value: "u25",
        label: "Under 25%",
        eliteOnly: false
      },
      {
        value: "u30",
        label: "Under 30%",
        eliteOnly: false
      },
      {
        value: "u35",
        label: "Under 35%",
        eliteOnly: false
      },
      {
        value: "u40",
        label: "Under 40%",
        eliteOnly: false
      },
      {
        value: "u45",
        label: "Under 45%",
        eliteOnly: false
      },
      {
        value: "u5",
        label: "Under 5%",
        eliteOnly: false
      },
      {
        value: "u50",
        label: "Under 50%",
        eliteOnly: false
      },
      {
        value: "u60",
        label: "Under 60%",
        eliteOnly: false
      },
      {
        value: "u70",
        label: "Under 70%",
        eliteOnly: false
      },
      {
        value: "u80",
        label: "Under 80%",
        eliteOnly: false
      },
      {
        value: "u90",
        label: "Under 90%",
        eliteOnly: false
      },
      {
        value: "custom_subscription",
        label: "Custom (Elite only)",
        eliteOnly: true
      }
    ]
  },
  fa_ltdebteq: {
    key: "fa_ltdebteq",
    label: "LT Debt/Equity",
    dataFilter: "fa_ltdebteq",
    groups: [
      "fundamental",
      "all"
    ],
    options: [
      {
        value: "",
        label: "Any",
        eliteOnly: false
      },
      {
        value: "high",
        label: "High (>0.5)",
        eliteOnly: false
      },
      {
        value: "low",
        label: "Low (<0.1)",
        eliteOnly: false
      },
      {
        value: "o0.1",
        label: "Over 0.1",
        eliteOnly: false
      },
      {
        value: "o0.2",
        label: "Over 0.2",
        eliteOnly: false
      },
      {
        value: "o0.3",
        label: "Over 0.3",
        eliteOnly: false
      },
      {
        value: "o0.4",
        label: "Over 0.4",
        eliteOnly: false
      },
      {
        value: "o0.5",
        label: "Over 0.5",
        eliteOnly: false
      },
      {
        value: "o0.6",
        label: "Over 0.6",
        eliteOnly: false
      },
      {
        value: "o0.7",
        label: "Over 0.7",
        eliteOnly: false
      },
      {
        value: "o0.8",
        label: "Over 0.8",
        eliteOnly: false
      },
      {
        value: "o0.9",
        label: "Over 0.9",
        eliteOnly: false
      },
      {
        value: "o1",
        label: "Over 1",
        eliteOnly: false
      },
      {
        value: "u0.1",
        label: "Under 0.1",
        eliteOnly: false
      },
      {
        value: "u0.2",
        label: "Under 0.2",
        eliteOnly: false
      },
      {
        value: "u0.3",
        label: "Under 0.3",
        eliteOnly: false
      },
      {
        value: "u0.4",
        label: "Under 0.4",
        eliteOnly: false
      },
      {
        value: "u0.5",
        label: "Under 0.5",
        eliteOnly: false
      },
      {
        value: "u0.6",
        label: "Under 0.6",
        eliteOnly: false
      },
      {
        value: "u0.7",
        label: "Under 0.7",
        eliteOnly: false
      },
      {
        value: "u0.8",
        label: "Under 0.8",
        eliteOnly: false
      },
      {
        value: "u0.9",
        label: "Under 0.9",
        eliteOnly: false
      },
      {
        value: "u1",
        label: "Under 1",
        eliteOnly: false
      },
      {
        value: "custom_subscription",
        label: "Custom (Elite only)",
        eliteOnly: true
      }
    ]
  },
  fa_netmargin: {
    key: "fa_netmargin",
    label: "Net Profit Margin",
    dataFilter: "fa_netmargin",
    groups: [
      "fundamental",
      "all"
    ],
    options: [
      {
        value: "",
        label: "Any",
        eliteOnly: false
      },
      {
        value: "high",
        label: "High (>20%)",
        eliteOnly: false
      },
      {
        value: "neg",
        label: "Negative (<0%)",
        eliteOnly: false
      },
      {
        value: "o0",
        label: "Over 0%",
        eliteOnly: false
      },
      {
        value: "o10",
        label: "Over 10%",
        eliteOnly: false
      },
      {
        value: "o15",
        label: "Over 15%",
        eliteOnly: false
      },
      {
        value: "o20",
        label: "Over 20%",
        eliteOnly: false
      },
      {
        value: "o25",
        label: "Over 25%",
        eliteOnly: false
      },
      {
        value: "o30",
        label: "Over 30%",
        eliteOnly: false
      },
      {
        value: "o35",
        label: "Over 35%",
        eliteOnly: false
      },
      {
        value: "o40",
        label: "Over 40%",
        eliteOnly: false
      },
      {
        value: "o45",
        label: "Over 45%",
        eliteOnly: false
      },
      {
        value: "o5",
        label: "Over 5%",
        eliteOnly: false
      },
      {
        value: "o50",
        label: "Over 50%",
        eliteOnly: false
      },
      {
        value: "o60",
        label: "Over 60%",
        eliteOnly: false
      },
      {
        value: "o70",
        label: "Over 70%",
        eliteOnly: false
      },
      {
        value: "o80",
        label: "Over 80%",
        eliteOnly: false
      },
      {
        value: "o90",
        label: "Over 90%",
        eliteOnly: false
      },
      {
        value: "pos",
        label: "Positive (>0%)",
        eliteOnly: false
      },
      {
        value: "u-10",
        label: "Under -10%",
        eliteOnly: false
      },
      {
        value: "u-100",
        label: "Under -100%",
        eliteOnly: false
      },
      {
        value: "u-20",
        label: "Under -20%",
        eliteOnly: false
      },
      {
        value: "u-30",
        label: "Under -30%",
        eliteOnly: false
      },
      {
        value: "u-50",
        label: "Under -50%",
        eliteOnly: false
      },
      {
        value: "u-70",
        label: "Under -70%",
        eliteOnly: false
      },
      {
        value: "u0",
        label: "Under 0%",
        eliteOnly: false
      },
      {
        value: "u10",
        label: "Under 10%",
        eliteOnly: false
      },
      {
        value: "u15",
        label: "Under 15%",
        eliteOnly: false
      },
      {
        value: "u20",
        label: "Under 20%",
        eliteOnly: false
      },
      {
        value: "u25",
        label: "Under 25%",
        eliteOnly: false
      },
      {
        value: "u30",
        label: "Under 30%",
        eliteOnly: false
      },
      {
        value: "u35",
        label: "Under 35%",
        eliteOnly: false
      },
      {
        value: "u40",
        label: "Under 40%",
        eliteOnly: false
      },
      {
        value: "u45",
        label: "Under 45%",
        eliteOnly: false
      },
      {
        value: "u5",
        label: "Under 5%",
        eliteOnly: false
      },
      {
        value: "u50",
        label: "Under 50%",
        eliteOnly: false
      },
      {
        value: "u60",
        label: "Under 60%",
        eliteOnly: false
      },
      {
        value: "u70",
        label: "Under 70%",
        eliteOnly: false
      },
      {
        value: "u80",
        label: "Under 80%",
        eliteOnly: false
      },
      {
        value: "u90",
        label: "Under 90%",
        eliteOnly: false
      },
      {
        value: "veryneg",
        label: "Very Negative (<-20%)",
        eliteOnly: false
      },
      {
        value: "custom_subscription",
        label: "Custom (Elite only)",
        eliteOnly: true
      }
    ]
  },
  fa_opermargin: {
    key: "fa_opermargin",
    label: "Operating Margin",
    dataFilter: "fa_opermargin",
    groups: [
      "fundamental",
      "all"
    ],
    options: [
      {
        value: "",
        label: "Any",
        eliteOnly: false
      },
      {
        value: "high",
        label: "High (>25%)",
        eliteOnly: false
      },
      {
        value: "neg",
        label: "Negative (<0%)",
        eliteOnly: false
      },
      {
        value: "o0",
        label: "Over 0%",
        eliteOnly: false
      },
      {
        value: "o10",
        label: "Over 10%",
        eliteOnly: false
      },
      {
        value: "o15",
        label: "Over 15%",
        eliteOnly: false
      },
      {
        value: "o20",
        label: "Over 20%",
        eliteOnly: false
      },
      {
        value: "o25",
        label: "Over 25%",
        eliteOnly: false
      },
      {
        value: "o30",
        label: "Over 30%",
        eliteOnly: false
      },
      {
        value: "o35",
        label: "Over 35%",
        eliteOnly: false
      },
      {
        value: "o40",
        label: "Over 40%",
        eliteOnly: false
      },
      {
        value: "o45",
        label: "Over 45%",
        eliteOnly: false
      },
      {
        value: "o5",
        label: "Over 5%",
        eliteOnly: false
      },
      {
        value: "o50",
        label: "Over 50%",
        eliteOnly: false
      },
      {
        value: "o60",
        label: "Over 60%",
        eliteOnly: false
      },
      {
        value: "o70",
        label: "Over 70%",
        eliteOnly: false
      },
      {
        value: "o80",
        label: "Over 80%",
        eliteOnly: false
      },
      {
        value: "o90",
        label: "Over 90%",
        eliteOnly: false
      },
      {
        value: "pos",
        label: "Positive (>0%)",
        eliteOnly: false
      },
      {
        value: "u-10",
        label: "Under -10%",
        eliteOnly: false
      },
      {
        value: "u-100",
        label: "Under -100%",
        eliteOnly: false
      },
      {
        value: "u-20",
        label: "Under -20%",
        eliteOnly: false
      },
      {
        value: "u-30",
        label: "Under -30%",
        eliteOnly: false
      },
      {
        value: "u-50",
        label: "Under -50%",
        eliteOnly: false
      },
      {
        value: "u-70",
        label: "Under -70%",
        eliteOnly: false
      },
      {
        value: "u0",
        label: "Under 0%",
        eliteOnly: false
      },
      {
        value: "u10",
        label: "Under 10%",
        eliteOnly: false
      },
      {
        value: "u15",
        label: "Under 15%",
        eliteOnly: false
      },
      {
        value: "u20",
        label: "Under 20%",
        eliteOnly: false
      },
      {
        value: "u25",
        label: "Under 25%",
        eliteOnly: false
      },
      {
        value: "u30",
        label: "Under 30%",
        eliteOnly: false
      },
      {
        value: "u35",
        label: "Under 35%",
        eliteOnly: false
      },
      {
        value: "u40",
        label: "Under 40%",
        eliteOnly: false
      },
      {
        value: "u45",
        label: "Under 45%",
        eliteOnly: false
      },
      {
        value: "u5",
        label: "Under 5%",
        eliteOnly: false
      },
      {
        value: "u50",
        label: "Under 50%",
        eliteOnly: false
      },
      {
        value: "u60",
        label: "Under 60%",
        eliteOnly: false
      },
      {
        value: "u70",
        label: "Under 70%",
        eliteOnly: false
      },
      {
        value: "u80",
        label: "Under 80%",
        eliteOnly: false
      },
      {
        value: "u90",
        label: "Under 90%",
        eliteOnly: false
      },
      {
        value: "veryneg",
        label: "Very Negative (<-20%)",
        eliteOnly: false
      },
      {
        value: "custom_subscription",
        label: "Custom (Elite only)",
        eliteOnly: true
      }
    ]
  },
  fa_payoutratio: {
    key: "fa_payoutratio",
    label: "Payout Ratio",
    dataFilter: "fa_payoutratio",
    groups: [
      "fundamental",
      "all"
    ],
    options: [
      {
        value: "",
        label: "Any",
        eliteOnly: false
      },
      {
        value: "high",
        label: "High (>50%)",
        eliteOnly: false
      },
      {
        value: "low",
        label: "Low (<20%)",
        eliteOnly: false
      },
      {
        value: "none",
        label: "None (0%)",
        eliteOnly: false
      },
      {
        value: "o0",
        label: "Over 0%",
        eliteOnly: false
      },
      {
        value: "o10",
        label: "Over 10%",
        eliteOnly: false
      },
      {
        value: "o100",
        label: "Over 100%",
        eliteOnly: false
      },
      {
        value: "o20",
        label: "Over 20%",
        eliteOnly: false
      },
      {
        value: "o30",
        label: "Over 30%",
        eliteOnly: false
      },
      {
        value: "o40",
        label: "Over 40%",
        eliteOnly: false
      },
      {
        value: "o50",
        label: "Over 50%",
        eliteOnly: false
      },
      {
        value: "o60",
        label: "Over 60%",
        eliteOnly: false
      },
      {
        value: "o70",
        label: "Over 70%",
        eliteOnly: false
      },
      {
        value: "o80",
        label: "Over 80%",
        eliteOnly: false
      },
      {
        value: "o90",
        label: "Over 90%",
        eliteOnly: false
      },
      {
        value: "pos",
        label: "Positive (>0%)",
        eliteOnly: false
      },
      {
        value: "u10",
        label: "Under 10%",
        eliteOnly: false
      },
      {
        value: "u100",
        label: "Under 100%",
        eliteOnly: false
      },
      {
        value: "u20",
        label: "Under 20%",
        eliteOnly: false
      },
      {
        value: "u30",
        label: "Under 30%",
        eliteOnly: false
      },
      {
        value: "u40",
        label: "Under 40%",
        eliteOnly: false
      },
      {
        value: "u50",
        label: "Under 50%",
        eliteOnly: false
      },
      {
        value: "u60",
        label: "Under 60%",
        eliteOnly: false
      },
      {
        value: "u70",
        label: "Under 70%",
        eliteOnly: false
      },
      {
        value: "u80",
        label: "Under 80%",
        eliteOnly: false
      },
      {
        value: "u90",
        label: "Under 90%",
        eliteOnly: false
      },
      {
        value: "custom_subscription",
        label: "Custom (Elite only)",
        eliteOnly: true
      }
    ]
  },
  fa_pb: {
    key: "fa_pb",
    label: "P/B",
    dataFilter: "fa_pb",
    groups: [
      "fundamental",
      "all"
    ],
    options: [
      {
        value: "",
        label: "Any",
        eliteOnly: false
      },
      {
        value: "high",
        label: "High (>5)",
        eliteOnly: false
      },
      {
        value: "low",
        label: "Low (<1)",
        eliteOnly: false
      },
      {
        value: "o1",
        label: "Over 1",
        eliteOnly: false
      },
      {
        value: "o10",
        label: "Over 10",
        eliteOnly: false
      },
      {
        value: "o2",
        label: "Over 2",
        eliteOnly: false
      },
      {
        value: "o3",
        label: "Over 3",
        eliteOnly: false
      },
      {
        value: "o4",
        label: "Over 4",
        eliteOnly: false
      },
      {
        value: "o5",
        label: "Over 5",
        eliteOnly: false
      },
      {
        value: "o6",
        label: "Over 6",
        eliteOnly: false
      },
      {
        value: "o7",
        label: "Over 7",
        eliteOnly: false
      },
      {
        value: "o8",
        label: "Over 8",
        eliteOnly: false
      },
      {
        value: "o9",
        label: "Over 9",
        eliteOnly: false
      },
      {
        value: "u1",
        label: "Under 1",
        eliteOnly: false
      },
      {
        value: "u10",
        label: "Under 10",
        eliteOnly: false
      },
      {
        value: "u2",
        label: "Under 2",
        eliteOnly: false
      },
      {
        value: "u3",
        label: "Under 3",
        eliteOnly: false
      },
      {
        value: "u4",
        label: "Under 4",
        eliteOnly: false
      },
      {
        value: "u5",
        label: "Under 5",
        eliteOnly: false
      },
      {
        value: "u6",
        label: "Under 6",
        eliteOnly: false
      },
      {
        value: "u7",
        label: "Under 7",
        eliteOnly: false
      },
      {
        value: "u8",
        label: "Under 8",
        eliteOnly: false
      },
      {
        value: "u9",
        label: "Under 9",
        eliteOnly: false
      },
      {
        value: "custom_subscription",
        label: "Custom (Elite only)",
        eliteOnly: true
      }
    ]
  },
  fa_pc: {
    key: "fa_pc",
    label: "Price/Cash",
    dataFilter: "fa_pc",
    groups: [
      "fundamental",
      "all"
    ],
    options: [
      {
        value: "",
        label: "Any",
        eliteOnly: false
      },
      {
        value: "high",
        label: "High (>50)",
        eliteOnly: false
      },
      {
        value: "low",
        label: "Low (<3)",
        eliteOnly: false
      },
      {
        value: "o1",
        label: "Over 1",
        eliteOnly: false
      },
      {
        value: "o10",
        label: "Over 10",
        eliteOnly: false
      },
      {
        value: "o2",
        label: "Over 2",
        eliteOnly: false
      },
      {
        value: "o20",
        label: "Over 20",
        eliteOnly: false
      },
      {
        value: "o3",
        label: "Over 3",
        eliteOnly: false
      },
      {
        value: "o30",
        label: "Over 30",
        eliteOnly: false
      },
      {
        value: "o4",
        label: "Over 4",
        eliteOnly: false
      },
      {
        value: "o40",
        label: "Over 40",
        eliteOnly: false
      },
      {
        value: "o5",
        label: "Over 5",
        eliteOnly: false
      },
      {
        value: "o50",
        label: "Over 50",
        eliteOnly: false
      },
      {
        value: "o6",
        label: "Over 6",
        eliteOnly: false
      },
      {
        value: "o7",
        label: "Over 7",
        eliteOnly: false
      },
      {
        value: "o8",
        label: "Over 8",
        eliteOnly: false
      },
      {
        value: "o9",
        label: "Over 9",
        eliteOnly: false
      },
      {
        value: "u1",
        label: "Under 1",
        eliteOnly: false
      },
      {
        value: "u10",
        label: "Under 10",
        eliteOnly: false
      },
      {
        value: "u2",
        label: "Under 2",
        eliteOnly: false
      },
      {
        value: "u3",
        label: "Under 3",
        eliteOnly: false
      },
      {
        value: "u4",
        label: "Under 4",
        eliteOnly: false
      },
      {
        value: "u5",
        label: "Under 5",
        eliteOnly: false
      },
      {
        value: "u6",
        label: "Under 6",
        eliteOnly: false
      },
      {
        value: "u7",
        label: "Under 7",
        eliteOnly: false
      },
      {
        value: "u8",
        label: "Under 8",
        eliteOnly: false
      },
      {
        value: "u9",
        label: "Under 9",
        eliteOnly: false
      },
      {
        value: "custom_subscription",
        label: "Custom (Elite only)",
        eliteOnly: true
      }
    ]
  },
  fa_pe: {
    key: "fa_pe",
    label: "P/E",
    dataFilter: "fa_pe",
    groups: [
      "fundamental",
      "all"
    ],
    options: [
      {
        value: "",
        label: "Any",
        eliteOnly: false
      },
      {
        value: "high",
        label: "High (>50)",
        eliteOnly: false
      },
      {
        value: "low",
        label: "Low (<15)",
        eliteOnly: false
      },
      {
        value: "o10",
        label: "Over 10",
        eliteOnly: false
      },
      {
        value: "o15",
        label: "Over 15",
        eliteOnly: false
      },
      {
        value: "o20",
        label: "Over 20",
        eliteOnly: false
      },
      {
        value: "o25",
        label: "Over 25",
        eliteOnly: false
      },
      {
        value: "o30",
        label: "Over 30",
        eliteOnly: false
      },
      {
        value: "o35",
        label: "Over 35",
        eliteOnly: false
      },
      {
        value: "o40",
        label: "Over 40",
        eliteOnly: false
      },
      {
        value: "o45",
        label: "Over 45",
        eliteOnly: false
      },
      {
        value: "o5",
        label: "Over 5",
        eliteOnly: false
      },
      {
        value: "o50",
        label: "Over 50",
        eliteOnly: false
      },
      {
        value: "profitable",
        label: "Profitable (>0)",
        eliteOnly: false
      },
      {
        value: "u10",
        label: "Under 10",
        eliteOnly: false
      },
      {
        value: "u15",
        label: "Under 15",
        eliteOnly: false
      },
      {
        value: "u20",
        label: "Under 20",
        eliteOnly: false
      },
      {
        value: "u25",
        label: "Under 25",
        eliteOnly: false
      },
      {
        value: "u30",
        label: "Under 30",
        eliteOnly: false
      },
      {
        value: "u35",
        label: "Under 35",
        eliteOnly: false
      },
      {
        value: "u40",
        label: "Under 40",
        eliteOnly: false
      },
      {
        value: "u45",
        label: "Under 45",
        eliteOnly: false
      },
      {
        value: "u5",
        label: "Under 5",
        eliteOnly: false
      },
      {
        value: "u50",
        label: "Under 50",
        eliteOnly: false
      },
      {
        value: "custom_subscription",
        label: "Custom (Elite only)",
        eliteOnly: true
      }
    ]
  },
  fa_peg: {
    key: "fa_peg",
    label: "PEG",
    dataFilter: "fa_peg",
    groups: [
      "fundamental",
      "all"
    ],
    options: [
      {
        value: "",
        label: "Any",
        eliteOnly: false
      },
      {
        value: "high",
        label: "High (>2)",
        eliteOnly: false
      },
      {
        value: "low",
        label: "Low (<1)",
        eliteOnly: false
      },
      {
        value: "o1",
        label: "Over 1",
        eliteOnly: false
      },
      {
        value: "o2",
        label: "Over 2",
        eliteOnly: false
      },
      {
        value: "o3",
        label: "Over 3",
        eliteOnly: false
      },
      {
        value: "u1",
        label: "Under 1",
        eliteOnly: false
      },
      {
        value: "u2",
        label: "Under 2",
        eliteOnly: false
      },
      {
        value: "u3",
        label: "Under 3",
        eliteOnly: false
      },
      {
        value: "custom_subscription",
        label: "Custom (Elite only)",
        eliteOnly: true
      }
    ]
  },
  fa_pfcf: {
    key: "fa_pfcf",
    label: "Price/Free Cash Flow",
    dataFilter: "fa_pfcf",
    groups: [
      "fundamental",
      "all"
    ],
    options: [
      {
        value: "",
        label: "Any",
        eliteOnly: false
      },
      {
        value: "high",
        label: "High (>50)",
        eliteOnly: false
      },
      {
        value: "low",
        label: "Low (<15)",
        eliteOnly: false
      },
      {
        value: "o10",
        label: "Over 10",
        eliteOnly: false
      },
      {
        value: "o100",
        label: "Over 100",
        eliteOnly: false
      },
      {
        value: "o15",
        label: "Over 15",
        eliteOnly: false
      },
      {
        value: "o20",
        label: "Over 20",
        eliteOnly: false
      },
      {
        value: "o25",
        label: "Over 25",
        eliteOnly: false
      },
      {
        value: "o30",
        label: "Over 30",
        eliteOnly: false
      },
      {
        value: "o35",
        label: "Over 35",
        eliteOnly: false
      },
      {
        value: "o40",
        label: "Over 40",
        eliteOnly: false
      },
      {
        value: "o45",
        label: "Over 45",
        eliteOnly: false
      },
      {
        value: "o5",
        label: "Over 5",
        eliteOnly: false
      },
      {
        value: "o50",
        label: "Over 50",
        eliteOnly: false
      },
      {
        value: "o60",
        label: "Over 60",
        eliteOnly: false
      },
      {
        value: "o70",
        label: "Over 70",
        eliteOnly: false
      },
      {
        value: "o80",
        label: "Over 80",
        eliteOnly: false
      },
      {
        value: "o90",
        label: "Over 90",
        eliteOnly: false
      },
      {
        value: "u10",
        label: "Under 10",
        eliteOnly: false
      },
      {
        value: "u100",
        label: "Under 100",
        eliteOnly: false
      },
      {
        value: "u15",
        label: "Under 15",
        eliteOnly: false
      },
      {
        value: "u20",
        label: "Under 20",
        eliteOnly: false
      },
      {
        value: "u25",
        label: "Under 25",
        eliteOnly: false
      },
      {
        value: "u30",
        label: "Under 30",
        eliteOnly: false
      },
      {
        value: "u35",
        label: "Under 35",
        eliteOnly: false
      },
      {
        value: "u40",
        label: "Under 40",
        eliteOnly: false
      },
      {
        value: "u45",
        label: "Under 45",
        eliteOnly: false
      },
      {
        value: "u5",
        label: "Under 5",
        eliteOnly: false
      },
      {
        value: "u50",
        label: "Under 50",
        eliteOnly: false
      },
      {
        value: "u60",
        label: "Under 60",
        eliteOnly: false
      },
      {
        value: "u70",
        label: "Under 70",
        eliteOnly: false
      },
      {
        value: "u80",
        label: "Under 80",
        eliteOnly: false
      },
      {
        value: "u90",
        label: "Under 90",
        eliteOnly: false
      },
      {
        value: "custom_subscription",
        label: "Custom (Elite only)",
        eliteOnly: true
      }
    ]
  },
  fa_ps: {
    key: "fa_ps",
    label: "P/S",
    dataFilter: "fa_ps",
    groups: [
      "fundamental",
      "all"
    ],
    options: [
      {
        value: "",
        label: "Any",
        eliteOnly: false
      },
      {
        value: "high",
        label: "High (>10)",
        eliteOnly: false
      },
      {
        value: "low",
        label: "Low (<1)",
        eliteOnly: false
      },
      {
        value: "o1",
        label: "Over 1",
        eliteOnly: false
      },
      {
        value: "o10",
        label: "Over 10",
        eliteOnly: false
      },
      {
        value: "o2",
        label: "Over 2",
        eliteOnly: false
      },
      {
        value: "o3",
        label: "Over 3",
        eliteOnly: false
      },
      {
        value: "o4",
        label: "Over 4",
        eliteOnly: false
      },
      {
        value: "o5",
        label: "Over 5",
        eliteOnly: false
      },
      {
        value: "o6",
        label: "Over 6",
        eliteOnly: false
      },
      {
        value: "o7",
        label: "Over 7",
        eliteOnly: false
      },
      {
        value: "o8",
        label: "Over 8",
        eliteOnly: false
      },
      {
        value: "o9",
        label: "Over 9",
        eliteOnly: false
      },
      {
        value: "u1",
        label: "Under 1",
        eliteOnly: false
      },
      {
        value: "u10",
        label: "Under 10",
        eliteOnly: false
      },
      {
        value: "u2",
        label: "Under 2",
        eliteOnly: false
      },
      {
        value: "u3",
        label: "Under 3",
        eliteOnly: false
      },
      {
        value: "u4",
        label: "Under 4",
        eliteOnly: false
      },
      {
        value: "u5",
        label: "Under 5",
        eliteOnly: false
      },
      {
        value: "u6",
        label: "Under 6",
        eliteOnly: false
      },
      {
        value: "u7",
        label: "Under 7",
        eliteOnly: false
      },
      {
        value: "u8",
        label: "Under 8",
        eliteOnly: false
      },
      {
        value: "u9",
        label: "Under 9",
        eliteOnly: false
      },
      {
        value: "custom_subscription",
        label: "Custom (Elite only)",
        eliteOnly: true
      }
    ]
  },
  fa_quickratio: {
    key: "fa_quickratio",
    label: "Quick Ratio",
    dataFilter: "fa_quickratio",
    groups: [
      "fundamental",
      "all"
    ],
    options: [
      {
        value: "",
        label: "Any",
        eliteOnly: false
      },
      {
        value: "high",
        label: "High (>3)",
        eliteOnly: false
      },
      {
        value: "low",
        label: "Low (<0.5)",
        eliteOnly: false
      },
      {
        value: "o0.5",
        label: "Over 0.5",
        eliteOnly: false
      },
      {
        value: "o1",
        label: "Over 1",
        eliteOnly: false
      },
      {
        value: "o1.5",
        label: "Over 1.5",
        eliteOnly: false
      },
      {
        value: "o10",
        label: "Over 10",
        eliteOnly: false
      },
      {
        value: "o2",
        label: "Over 2",
        eliteOnly: false
      },
      {
        value: "o3",
        label: "Over 3",
        eliteOnly: false
      },
      {
        value: "o4",
        label: "Over 4",
        eliteOnly: false
      },
      {
        value: "o5",
        label: "Over 5",
        eliteOnly: false
      },
      {
        value: "u0.5",
        label: "Under 0.5",
        eliteOnly: false
      },
      {
        value: "u1",
        label: "Under 1",
        eliteOnly: false
      },
      {
        value: "custom_subscription",
        label: "Custom (Elite only)",
        eliteOnly: true
      }
    ]
  },
  fa_roa: {
    key: "fa_roa",
    label: "Return on Assets",
    dataFilter: "fa_roa",
    groups: [
      "fundamental",
      "all"
    ],
    options: [
      {
        value: "",
        label: "Any",
        eliteOnly: false
      },
      {
        value: "neg",
        label: "Negative (<0%)",
        eliteOnly: false
      },
      {
        value: "o10",
        label: "Over +10%",
        eliteOnly: false
      },
      {
        value: "o15",
        label: "Over +15%",
        eliteOnly: false
      },
      {
        value: "o20",
        label: "Over +20%",
        eliteOnly: false
      },
      {
        value: "o25",
        label: "Over +25%",
        eliteOnly: false
      },
      {
        value: "o30",
        label: "Over +30%",
        eliteOnly: false
      },
      {
        value: "o35",
        label: "Over +35%",
        eliteOnly: false
      },
      {
        value: "o40",
        label: "Over +40%",
        eliteOnly: false
      },
      {
        value: "o45",
        label: "Over +45%",
        eliteOnly: false
      },
      {
        value: "o5",
        label: "Over +5%",
        eliteOnly: false
      },
      {
        value: "o50",
        label: "Over +50%",
        eliteOnly: false
      },
      {
        value: "pos",
        label: "Positive (>0%)",
        eliteOnly: false
      },
      {
        value: "u-10",
        label: "Under -10%",
        eliteOnly: false
      },
      {
        value: "u-15",
        label: "Under -15%",
        eliteOnly: false
      },
      {
        value: "u-20",
        label: "Under -20%",
        eliteOnly: false
      },
      {
        value: "u-25",
        label: "Under -25%",
        eliteOnly: false
      },
      {
        value: "u-30",
        label: "Under -30%",
        eliteOnly: false
      },
      {
        value: "u-35",
        label: "Under -35%",
        eliteOnly: false
      },
      {
        value: "u-40",
        label: "Under -40%",
        eliteOnly: false
      },
      {
        value: "u-45",
        label: "Under -45%",
        eliteOnly: false
      },
      {
        value: "u-5",
        label: "Under -5%",
        eliteOnly: false
      },
      {
        value: "u-50",
        label: "Under -50%",
        eliteOnly: false
      },
      {
        value: "veryneg",
        label: "Very Negative (<-15%)",
        eliteOnly: false
      },
      {
        value: "verypos",
        label: "Very Positive (>15%)",
        eliteOnly: false
      },
      {
        value: "custom_subscription",
        label: "Custom (Elite only)",
        eliteOnly: true
      }
    ]
  },
  fa_roe: {
    key: "fa_roe",
    label: "Return on Equity",
    dataFilter: "fa_roe",
    groups: [
      "fundamental",
      "all"
    ],
    options: [
      {
        value: "",
        label: "Any",
        eliteOnly: false
      },
      {
        value: "neg",
        label: "Negative (<0%)",
        eliteOnly: false
      },
      {
        value: "o10",
        label: "Over +10%",
        eliteOnly: false
      },
      {
        value: "o15",
        label: "Over +15%",
        eliteOnly: false
      },
      {
        value: "o20",
        label: "Over +20%",
        eliteOnly: false
      },
      {
        value: "o25",
        label: "Over +25%",
        eliteOnly: false
      },
      {
        value: "o30",
        label: "Over +30%",
        eliteOnly: false
      },
      {
        value: "o35",
        label: "Over +35%",
        eliteOnly: false
      },
      {
        value: "o40",
        label: "Over +40%",
        eliteOnly: false
      },
      {
        value: "o45",
        label: "Over +45%",
        eliteOnly: false
      },
      {
        value: "o5",
        label: "Over +5%",
        eliteOnly: false
      },
      {
        value: "o50",
        label: "Over +50%",
        eliteOnly: false
      },
      {
        value: "pos",
        label: "Positive (>0%)",
        eliteOnly: false
      },
      {
        value: "u-10",
        label: "Under -10%",
        eliteOnly: false
      },
      {
        value: "u-15",
        label: "Under -15%",
        eliteOnly: false
      },
      {
        value: "u-20",
        label: "Under -20%",
        eliteOnly: false
      },
      {
        value: "u-25",
        label: "Under -25%",
        eliteOnly: false
      },
      {
        value: "u-30",
        label: "Under -30%",
        eliteOnly: false
      },
      {
        value: "u-35",
        label: "Under -35%",
        eliteOnly: false
      },
      {
        value: "u-40",
        label: "Under -40%",
        eliteOnly: false
      },
      {
        value: "u-45",
        label: "Under -45%",
        eliteOnly: false
      },
      {
        value: "u-5",
        label: "Under -5%",
        eliteOnly: false
      },
      {
        value: "u-50",
        label: "Under -50%",
        eliteOnly: false
      },
      {
        value: "veryneg",
        label: "Very Negative (<-15%)",
        eliteOnly: false
      },
      {
        value: "verypos",
        label: "Very Positive (>30%)",
        eliteOnly: false
      },
      {
        value: "custom_subscription",
        label: "Custom (Elite only)",
        eliteOnly: true
      }
    ]
  },
  fa_roi: {
    key: "fa_roi",
    label: "Return on Invested Capital",
    dataFilter: "fa_roi",
    groups: [
      "fundamental",
      "all"
    ],
    options: [
      {
        value: "",
        label: "Any",
        eliteOnly: false
      },
      {
        value: "neg",
        label: "Negative (<0%)",
        eliteOnly: false
      },
      {
        value: "o10",
        label: "Over +10%",
        eliteOnly: false
      },
      {
        value: "o15",
        label: "Over +15%",
        eliteOnly: false
      },
      {
        value: "o20",
        label: "Over +20%",
        eliteOnly: false
      },
      {
        value: "o25",
        label: "Over +25%",
        eliteOnly: false
      },
      {
        value: "o30",
        label: "Over +30%",
        eliteOnly: false
      },
      {
        value: "o35",
        label: "Over +35%",
        eliteOnly: false
      },
      {
        value: "o40",
        label: "Over +40%",
        eliteOnly: false
      },
      {
        value: "o45",
        label: "Over +45%",
        eliteOnly: false
      },
      {
        value: "o5",
        label: "Over +5%",
        eliteOnly: false
      },
      {
        value: "o50",
        label: "Over +50%",
        eliteOnly: false
      },
      {
        value: "pos",
        label: "Positive (>0%)",
        eliteOnly: false
      },
      {
        value: "u-10",
        label: "Under -10%",
        eliteOnly: false
      },
      {
        value: "u-15",
        label: "Under -15%",
        eliteOnly: false
      },
      {
        value: "u-20",
        label: "Under -20%",
        eliteOnly: false
      },
      {
        value: "u-25",
        label: "Under -25%",
        eliteOnly: false
      },
      {
        value: "u-30",
        label: "Under -30%",
        eliteOnly: false
      },
      {
        value: "u-35",
        label: "Under -35%",
        eliteOnly: false
      },
      {
        value: "u-40",
        label: "Under -40%",
        eliteOnly: false
      },
      {
        value: "u-45",
        label: "Under -45%",
        eliteOnly: false
      },
      {
        value: "u-5",
        label: "Under -5%",
        eliteOnly: false
      },
      {
        value: "u-50",
        label: "Under -50%",
        eliteOnly: false
      },
      {
        value: "veryneg",
        label: "Very Negative (<-10%)",
        eliteOnly: false
      },
      {
        value: "verypos",
        label: "Very Positive (>25%)",
        eliteOnly: false
      },
      {
        value: "custom_subscription",
        label: "Custom (Elite only)",
        eliteOnly: true
      }
    ]
  },
  fa_sales3years: {
    key: "fa_sales3years",
    label: "Sales Growth Past 3 Years",
    dataFilter: "fa_sales3years",
    groups: [
      "fundamental",
      "all"
    ],
    options: [
      {
        value: "",
        label: "Any",
        eliteOnly: false
      },
      {
        value: "high",
        label: "High (>25%)",
        eliteOnly: false
      },
      {
        value: "neg",
        label: "Negative (<0%)",
        eliteOnly: false
      },
      {
        value: "o10",
        label: "Over 10%",
        eliteOnly: false
      },
      {
        value: "o15",
        label: "Over 15%",
        eliteOnly: false
      },
      {
        value: "o20",
        label: "Over 20%",
        eliteOnly: false
      },
      {
        value: "o25",
        label: "Over 25%",
        eliteOnly: false
      },
      {
        value: "o30",
        label: "Over 30%",
        eliteOnly: false
      },
      {
        value: "o5",
        label: "Over 5%",
        eliteOnly: false
      },
      {
        value: "pos",
        label: "Positive (>0%)",
        eliteOnly: false
      },
      {
        value: "poslow",
        label: "Positive Low (0-10%)",
        eliteOnly: false
      },
      {
        value: "u10",
        label: "Under 10%",
        eliteOnly: false
      },
      {
        value: "u15",
        label: "Under 15%",
        eliteOnly: false
      },
      {
        value: "u20",
        label: "Under 20%",
        eliteOnly: false
      },
      {
        value: "u25",
        label: "Under 25%",
        eliteOnly: false
      },
      {
        value: "u30",
        label: "Under 30%",
        eliteOnly: false
      },
      {
        value: "u5",
        label: "Under 5%",
        eliteOnly: false
      },
      {
        value: "custom_subscription",
        label: "Custom (Elite only)",
        eliteOnly: true
      }
    ]
  },
  fa_sales5years: {
    key: "fa_sales5years",
    label: "Sales Growth Past 5 Years",
    dataFilter: "fa_sales5years",
    groups: [
      "fundamental",
      "all"
    ],
    options: [
      {
        value: "",
        label: "Any",
        eliteOnly: false
      },
      {
        value: "high",
        label: "High (>25%)",
        eliteOnly: false
      },
      {
        value: "neg",
        label: "Negative (<0%)",
        eliteOnly: false
      },
      {
        value: "o10",
        label: "Over 10%",
        eliteOnly: false
      },
      {
        value: "o15",
        label: "Over 15%",
        eliteOnly: false
      },
      {
        value: "o20",
        label: "Over 20%",
        eliteOnly: false
      },
      {
        value: "o25",
        label: "Over 25%",
        eliteOnly: false
      },
      {
        value: "o30",
        label: "Over 30%",
        eliteOnly: false
      },
      {
        value: "o5",
        label: "Over 5%",
        eliteOnly: false
      },
      {
        value: "pos",
        label: "Positive (>0%)",
        eliteOnly: false
      },
      {
        value: "poslow",
        label: "Positive Low (0-10%)",
        eliteOnly: false
      },
      {
        value: "u10",
        label: "Under 10%",
        eliteOnly: false
      },
      {
        value: "u15",
        label: "Under 15%",
        eliteOnly: false
      },
      {
        value: "u20",
        label: "Under 20%",
        eliteOnly: false
      },
      {
        value: "u25",
        label: "Under 25%",
        eliteOnly: false
      },
      {
        value: "u30",
        label: "Under 30%",
        eliteOnly: false
      },
      {
        value: "u5",
        label: "Under 5%",
        eliteOnly: false
      },
      {
        value: "custom_subscription",
        label: "Custom (Elite only)",
        eliteOnly: true
      }
    ]
  },
  fa_salesqoq: {
    key: "fa_salesqoq",
    label: "Sales Growth Qtr Over Qtr",
    dataFilter: "fa_salesqoq",
    groups: [
      "fundamental",
      "all"
    ],
    options: [
      {
        value: "",
        label: "Any",
        eliteOnly: false
      },
      {
        value: "high",
        label: "High (>25%)",
        eliteOnly: false
      },
      {
        value: "neg",
        label: "Negative (<0%)",
        eliteOnly: false
      },
      {
        value: "o10",
        label: "Over 10%",
        eliteOnly: false
      },
      {
        value: "o15",
        label: "Over 15%",
        eliteOnly: false
      },
      {
        value: "o20",
        label: "Over 20%",
        eliteOnly: false
      },
      {
        value: "o25",
        label: "Over 25%",
        eliteOnly: false
      },
      {
        value: "o30",
        label: "Over 30%",
        eliteOnly: false
      },
      {
        value: "o5",
        label: "Over 5%",
        eliteOnly: false
      },
      {
        value: "pos",
        label: "Positive (>0%)",
        eliteOnly: false
      },
      {
        value: "poslow",
        label: "Positive Low (0-10%)",
        eliteOnly: false
      },
      {
        value: "u10",
        label: "Under 10%",
        eliteOnly: false
      },
      {
        value: "u15",
        label: "Under 15%",
        eliteOnly: false
      },
      {
        value: "u20",
        label: "Under 20%",
        eliteOnly: false
      },
      {
        value: "u25",
        label: "Under 25%",
        eliteOnly: false
      },
      {
        value: "u30",
        label: "Under 30%",
        eliteOnly: false
      },
      {
        value: "u5",
        label: "Under 5%",
        eliteOnly: false
      },
      {
        value: "custom_subscription",
        label: "Custom (Elite only)",
        eliteOnly: true
      }
    ]
  },
  fa_salesyoyttm: {
    key: "fa_salesyoyttm",
    label: "Sales Growth TTM",
    dataFilter: "fa_salesyoyttm",
    groups: [
      "fundamental",
      "all"
    ],
    options: [
      {
        value: "",
        label: "Any",
        eliteOnly: false
      },
      {
        value: "high",
        label: "High (>25%)",
        eliteOnly: false
      },
      {
        value: "neg",
        label: "Negative (<0%)",
        eliteOnly: false
      },
      {
        value: "o10",
        label: "Over 10%",
        eliteOnly: false
      },
      {
        value: "o15",
        label: "Over 15%",
        eliteOnly: false
      },
      {
        value: "o20",
        label: "Over 20%",
        eliteOnly: false
      },
      {
        value: "o25",
        label: "Over 25%",
        eliteOnly: false
      },
      {
        value: "o30",
        label: "Over 30%",
        eliteOnly: false
      },
      {
        value: "o5",
        label: "Over 5%",
        eliteOnly: false
      },
      {
        value: "pos",
        label: "Positive (>0%)",
        eliteOnly: false
      },
      {
        value: "poslow",
        label: "Positive Low (0-10%)",
        eliteOnly: false
      },
      {
        value: "u10",
        label: "Under 10%",
        eliteOnly: false
      },
      {
        value: "u15",
        label: "Under 15%",
        eliteOnly: false
      },
      {
        value: "u20",
        label: "Under 20%",
        eliteOnly: false
      },
      {
        value: "u25",
        label: "Under 25%",
        eliteOnly: false
      },
      {
        value: "u30",
        label: "Under 30%",
        eliteOnly: false
      },
      {
        value: "u5",
        label: "Under 5%",
        eliteOnly: false
      },
      {
        value: "custom_subscription",
        label: "Custom (Elite only)",
        eliteOnly: true
      }
    ]
  },
  float: {
    key: "float",
    label: "Float",
    dataFilter: "sh_float",
    groups: [
      "descriptive",
      "all"
    ],
    options: [
      {
        value: "",
        label: "Any",
        eliteOnly: false
      },
      {
        value: "o10p",
        label: "Over 10%",
        eliteOnly: false
      },
      {
        value: "o1000",
        label: "Over 1000M",
        eliteOnly: false
      },
      {
        value: "o100",
        label: "Over 100M",
        eliteOnly: false
      },
      {
        value: "o10",
        label: "Over 10M",
        eliteOnly: false
      },
      {
        value: "o1",
        label: "Over 1M",
        eliteOnly: false
      },
      {
        value: "o20p",
        label: "Over 20%",
        eliteOnly: false
      },
      {
        value: "o200",
        label: "Over 200M",
        eliteOnly: false
      },
      {
        value: "o20",
        label: "Over 20M",
        eliteOnly: false
      },
      {
        value: "o2",
        label: "Over 2M",
        eliteOnly: false
      },
      {
        value: "o30p",
        label: "Over 30%",
        eliteOnly: false
      },
      {
        value: "o40p",
        label: "Over 40%",
        eliteOnly: false
      },
      {
        value: "o50p",
        label: "Over 50%",
        eliteOnly: false
      },
      {
        value: "o500",
        label: "Over 500M",
        eliteOnly: false
      },
      {
        value: "o50",
        label: "Over 50M",
        eliteOnly: false
      },
      {
        value: "o5",
        label: "Over 5M",
        eliteOnly: false
      },
      {
        value: "o60p",
        label: "Over 60%",
        eliteOnly: false
      },
      {
        value: "o70p",
        label: "Over 70%",
        eliteOnly: false
      },
      {
        value: "o80p",
        label: "Over 80%",
        eliteOnly: false
      },
      {
        value: "o90p",
        label: "Over 90%",
        eliteOnly: false
      },
      {
        value: "u10p",
        label: "Under 10%",
        eliteOnly: false
      },
      {
        value: "u100",
        label: "Under 100M",
        eliteOnly: false
      },
      {
        value: "u10",
        label: "Under 10M",
        eliteOnly: false
      },
      {
        value: "u1",
        label: "Under 1M",
        eliteOnly: false
      },
      {
        value: "u20p",
        label: "Under 20%",
        eliteOnly: false
      },
      {
        value: "u20",
        label: "Under 20M",
        eliteOnly: false
      },
      {
        value: "u30p",
        label: "Under 30%",
        eliteOnly: false
      },
      {
        value: "u40p",
        label: "Under 40%",
        eliteOnly: false
      },
      {
        value: "u50p",
        label: "Under 50%",
        eliteOnly: false
      },
      {
        value: "u50",
        label: "Under 50M",
        eliteOnly: false
      },
      {
        value: "u5",
        label: "Under 5M",
        eliteOnly: false
      },
      {
        value: "u60p",
        label: "Under 60%",
        eliteOnly: false
      },
      {
        value: "u70p",
        label: "Under 70%",
        eliteOnly: false
      },
      {
        value: "u80p",
        label: "Under 80%",
        eliteOnly: false
      },
      {
        value: "u90p",
        label: "Under 90%",
        eliteOnly: false
      },
      {
        value: "custom_subscription",
        label: "Custom (Elite only)",
        eliteOnly: true
      }
    ]
  },
  index: {
    key: "index",
    label: "Index",
    dataFilter: "idx",
    groups: [
      "descriptive",
      "all"
    ],
    options: [
      {
        value: "",
        label: "Any",
        eliteOnly: false
      },
      {
        value: "dji",
        label: "DJIA",
        eliteOnly: false
      },
      {
        value: "ndx",
        label: "NASDAQ 100",
        eliteOnly: false
      },
      {
        value: "rut",
        label: "RUSSELL 2000",
        eliteOnly: false
      },
      {
        value: "sp500",
        label: "S&P 500",
        eliteOnly: false
      },
      {
        value: "custom_subscription",
        label: "Custom (Elite only)",
        eliteOnly: true
      }
    ]
  },
  industry: {
    key: "industry",
    label: "Industry",
    dataFilter: "ind",
    groups: [
      "descriptive",
      "all"
    ],
    options: [
      {
        value: "",
        label: "Any",
        eliteOnly: false
      },
      {
        value: "advertisingagencies",
        label: "Advertising Agencies",
        eliteOnly: false
      },
      {
        value: "aerospacedefense",
        label: "Aerospace & Defense",
        eliteOnly: false
      },
      {
        value: "agriculturalinputs",
        label: "Agricultural Inputs",
        eliteOnly: false
      },
      {
        value: "airlines",
        label: "Airlines",
        eliteOnly: false
      },
      {
        value: "airportsairservices",
        label: "Airports & Air Services",
        eliteOnly: false
      },
      {
        value: "aluminum",
        label: "Aluminum",
        eliteOnly: false
      },
      {
        value: "apparelmanufacturing",
        label: "Apparel Manufacturing",
        eliteOnly: false
      },
      {
        value: "apparelretail",
        label: "Apparel Retail",
        eliteOnly: false
      },
      {
        value: "assetmanagement",
        label: "Asset Management",
        eliteOnly: false
      },
      {
        value: "autotruckdealerships",
        label: "Auto & Truck Dealerships",
        eliteOnly: false
      },
      {
        value: "automanufacturers",
        label: "Auto Manufacturers",
        eliteOnly: false
      },
      {
        value: "autoparts",
        label: "Auto Parts",
        eliteOnly: false
      },
      {
        value: "banksdiversified",
        label: "Banks - Diversified",
        eliteOnly: false
      },
      {
        value: "banksregional",
        label: "Banks - Regional",
        eliteOnly: false
      },
      {
        value: "beveragesbrewers",
        label: "Beverages - Brewers",
        eliteOnly: false
      },
      {
        value: "beveragesnonalcoholic",
        label: "Beverages - Non-Alcoholic",
        eliteOnly: false
      },
      {
        value: "beverageswineriesdistilleries",
        label: "Beverages - Wineries & Distilleries",
        eliteOnly: false
      },
      {
        value: "biotechnology",
        label: "Biotechnology",
        eliteOnly: false
      },
      {
        value: "broadcasting",
        label: "Broadcasting",
        eliteOnly: false
      },
      {
        value: "buildingmaterials",
        label: "Building Materials",
        eliteOnly: false
      },
      {
        value: "buildingproductsequipment",
        label: "Building Products & Equipment",
        eliteOnly: false
      },
      {
        value: "businessequipmentsupplies",
        label: "Business Equipment & Supplies",
        eliteOnly: false
      },
      {
        value: "capitalmarkets",
        label: "Capital Markets",
        eliteOnly: false
      },
      {
        value: "chemicals",
        label: "Chemicals",
        eliteOnly: false
      },
      {
        value: "closedendfunddebt",
        label: "Closed-End Fund - Debt",
        eliteOnly: false
      },
      {
        value: "closedendfundequity",
        label: "Closed-End Fund - Equity",
        eliteOnly: false
      },
      {
        value: "closedendfundforeign",
        label: "Closed-End Fund - Foreign",
        eliteOnly: false
      },
      {
        value: "cokingcoal",
        label: "Coking Coal",
        eliteOnly: false
      },
      {
        value: "communicationequipment",
        label: "Communication Equipment",
        eliteOnly: false
      },
      {
        value: "computerhardware",
        label: "Computer Hardware",
        eliteOnly: false
      },
      {
        value: "confectioners",
        label: "Confectioners",
        eliteOnly: false
      },
      {
        value: "conglomerates",
        label: "Conglomerates",
        eliteOnly: false
      },
      {
        value: "consultingservices",
        label: "Consulting Services",
        eliteOnly: false
      },
      {
        value: "consumerelectronics",
        label: "Consumer Electronics",
        eliteOnly: false
      },
      {
        value: "copper",
        label: "Copper",
        eliteOnly: false
      },
      {
        value: "creditservices",
        label: "Credit Services",
        eliteOnly: false
      },
      {
        value: "departmentstores",
        label: "Department Stores",
        eliteOnly: false
      },
      {
        value: "diagnosticsresearch",
        label: "Diagnostics & Research",
        eliteOnly: false
      },
      {
        value: "discountstores",
        label: "Discount Stores",
        eliteOnly: false
      },
      {
        value: "drugmanufacturersgeneral",
        label: "Drug Manufacturers - General",
        eliteOnly: false
      },
      {
        value: "drugmanufacturersspecialtygeneric",
        label: "Drug Manufacturers - Specialty & Generic",
        eliteOnly: false
      },
      {
        value: "educationtrainingservices",
        label: "Education & Training Services",
        eliteOnly: false
      },
      {
        value: "electricalequipmentparts",
        label: "Electrical Equipment & Parts",
        eliteOnly: false
      },
      {
        value: "electroniccomponents",
        label: "Electronic Components",
        eliteOnly: false
      },
      {
        value: "electronicgamingmultimedia",
        label: "Electronic Gaming & Multimedia",
        eliteOnly: false
      },
      {
        value: "electronicscomputerdistribution",
        label: "Electronics & Computer Distribution",
        eliteOnly: false
      },
      {
        value: "engineeringconstruction",
        label: "Engineering & Construction",
        eliteOnly: false
      },
      {
        value: "entertainment",
        label: "Entertainment",
        eliteOnly: false
      },
      {
        value: "exchangetradedfund",
        label: "Exchange Traded Fund",
        eliteOnly: false
      },
      {
        value: "farmheavyconstructionmachinery",
        label: "Farm & Heavy Construction Machinery",
        eliteOnly: false
      },
      {
        value: "farmproducts",
        label: "Farm Products",
        eliteOnly: false
      },
      {
        value: "financialconglomerates",
        label: "Financial Conglomerates",
        eliteOnly: false
      },
      {
        value: "financialdatastockexchanges",
        label: "Financial Data & Stock Exchanges",
        eliteOnly: false
      },
      {
        value: "fooddistribution",
        label: "Food Distribution",
        eliteOnly: false
      },
      {
        value: "footwearaccessories",
        label: "Footwear & Accessories",
        eliteOnly: false
      },
      {
        value: "furnishingsfixturesappliances",
        label: "Furnishings, Fixtures & Appliances",
        eliteOnly: false
      },
      {
        value: "gambling",
        label: "Gambling",
        eliteOnly: false
      },
      {
        value: "gold",
        label: "Gold",
        eliteOnly: false
      },
      {
        value: "grocerystores",
        label: "Grocery Stores",
        eliteOnly: false
      },
      {
        value: "healthinformationservices",
        label: "Health Information Services",
        eliteOnly: false
      },
      {
        value: "healthcareplans",
        label: "Healthcare Plans",
        eliteOnly: false
      },
      {
        value: "homeimprovementretail",
        label: "Home Improvement Retail",
        eliteOnly: false
      },
      {
        value: "householdpersonalproducts",
        label: "Household & Personal Products",
        eliteOnly: false
      },
      {
        value: "industrialdistribution",
        label: "Industrial Distribution",
        eliteOnly: false
      },
      {
        value: "informationtechnologyservices",
        label: "Information Technology Services",
        eliteOnly: false
      },
      {
        value: "infrastructureoperations",
        label: "Infrastructure Operations",
        eliteOnly: false
      },
      {
        value: "insurancediversified",
        label: "Insurance - Diversified",
        eliteOnly: false
      },
      {
        value: "insurancelife",
        label: "Insurance - Life",
        eliteOnly: false
      },
      {
        value: "insurancepropertycasualty",
        label: "Insurance - Property & Casualty",
        eliteOnly: false
      },
      {
        value: "insurancereinsurance",
        label: "Insurance - Reinsurance",
        eliteOnly: false
      },
      {
        value: "insurancespecialty",
        label: "Insurance - Specialty",
        eliteOnly: false
      },
      {
        value: "insurancebrokers",
        label: "Insurance Brokers",
        eliteOnly: false
      },
      {
        value: "integratedfreightlogistics",
        label: "Integrated Freight & Logistics",
        eliteOnly: false
      },
      {
        value: "internetcontentinformation",
        label: "Internet Content & Information",
        eliteOnly: false
      },
      {
        value: "internetretail",
        label: "Internet Retail",
        eliteOnly: false
      },
      {
        value: "leisure",
        label: "Leisure",
        eliteOnly: false
      },
      {
        value: "lodging",
        label: "Lodging",
        eliteOnly: false
      },
      {
        value: "lumberwoodproduction",
        label: "Lumber & Wood Production",
        eliteOnly: false
      },
      {
        value: "luxurygoods",
        label: "Luxury Goods",
        eliteOnly: false
      },
      {
        value: "marineshipping",
        label: "Marine Shipping",
        eliteOnly: false
      },
      {
        value: "medicalcarefacilities",
        label: "Medical Care Facilities",
        eliteOnly: false
      },
      {
        value: "medicaldevices",
        label: "Medical Devices",
        eliteOnly: false
      },
      {
        value: "medicaldistribution",
        label: "Medical Distribution",
        eliteOnly: false
      },
      {
        value: "medicalinstrumentssupplies",
        label: "Medical Instruments & Supplies",
        eliteOnly: false
      },
      {
        value: "metalfabrication",
        label: "Metal Fabrication",
        eliteOnly: false
      },
      {
        value: "mortgagefinance",
        label: "Mortgage Finance",
        eliteOnly: false
      },
      {
        value: "oilgasdrilling",
        label: "Oil & Gas Drilling",
        eliteOnly: false
      },
      {
        value: "oilgasep",
        label: "Oil & Gas E&P",
        eliteOnly: false
      },
      {
        value: "oilgasequipmentservices",
        label: "Oil & Gas Equipment & Services",
        eliteOnly: false
      },
      {
        value: "oilgasintegrated",
        label: "Oil & Gas Integrated",
        eliteOnly: false
      },
      {
        value: "oilgasmidstream",
        label: "Oil & Gas Midstream",
        eliteOnly: false
      },
      {
        value: "oilgasrefiningmarketing",
        label: "Oil & Gas Refining & Marketing",
        eliteOnly: false
      },
      {
        value: "otherindustrialmetalsmining",
        label: "Other Industrial Metals & Mining",
        eliteOnly: false
      },
      {
        value: "otherpreciousmetalsmining",
        label: "Other Precious Metals & Mining",
        eliteOnly: false
      },
      {
        value: "packagedfoods",
        label: "Packaged Foods",
        eliteOnly: false
      },
      {
        value: "packagingcontainers",
        label: "Packaging & Containers",
        eliteOnly: false
      },
      {
        value: "paperpaperproducts",
        label: "Paper & Paper Products",
        eliteOnly: false
      },
      {
        value: "personalservices",
        label: "Personal Services",
        eliteOnly: false
      },
      {
        value: "pharmaceuticalretailers",
        label: "Pharmaceutical Retailers",
        eliteOnly: false
      },
      {
        value: "pollutiontreatmentcontrols",
        label: "Pollution & Treatment Controls",
        eliteOnly: false
      },
      {
        value: "publishing",
        label: "Publishing",
        eliteOnly: false
      },
      {
        value: "reitdiversified",
        label: "REIT - Diversified",
        eliteOnly: false
      },
      {
        value: "reithealthcarefacilities",
        label: "REIT - Healthcare Facilities",
        eliteOnly: false
      },
      {
        value: "reithotelmotel",
        label: "REIT - Hotel & Motel",
        eliteOnly: false
      },
      {
        value: "reitindustrial",
        label: "REIT - Industrial",
        eliteOnly: false
      },
      {
        value: "reitmortgage",
        label: "REIT - Mortgage",
        eliteOnly: false
      },
      {
        value: "reitoffice",
        label: "REIT - Office",
        eliteOnly: false
      },
      {
        value: "reitresidential",
        label: "REIT - Residential",
        eliteOnly: false
      },
      {
        value: "reitretail",
        label: "REIT - Retail",
        eliteOnly: false
      },
      {
        value: "reitspecialty",
        label: "REIT - Specialty",
        eliteOnly: false
      },
      {
        value: "railroads",
        label: "Railroads",
        eliteOnly: false
      },
      {
        value: "realestatedevelopment",
        label: "Real Estate - Development",
        eliteOnly: false
      },
      {
        value: "realestatediversified",
        label: "Real Estate - Diversified",
        eliteOnly: false
      },
      {
        value: "realestateservices",
        label: "Real Estate Services",
        eliteOnly: false
      },
      {
        value: "recreationalvehicles",
        label: "Recreational Vehicles",
        eliteOnly: false
      },
      {
        value: "rentalleasingservices",
        label: "Rental & Leasing Services",
        eliteOnly: false
      },
      {
        value: "residentialconstruction",
        label: "Residential Construction",
        eliteOnly: false
      },
      {
        value: "resortscasinos",
        label: "Resorts & Casinos",
        eliteOnly: false
      },
      {
        value: "restaurants",
        label: "Restaurants",
        eliteOnly: false
      },
      {
        value: "scientifictechnicalinstruments",
        label: "Scientific & Technical Instruments",
        eliteOnly: false
      },
      {
        value: "securityprotectionservices",
        label: "Security & Protection Services",
        eliteOnly: false
      },
      {
        value: "semiconductorequipmentmaterials",
        label: "Semiconductor Equipment & Materials",
        eliteOnly: false
      },
      {
        value: "semiconductors",
        label: "Semiconductors",
        eliteOnly: false
      },
      {
        value: "shellcompanies",
        label: "Shell Companies",
        eliteOnly: false
      },
      {
        value: "silver",
        label: "Silver",
        eliteOnly: false
      },
      {
        value: "softwareapplication",
        label: "Software - Application",
        eliteOnly: false
      },
      {
        value: "softwareinfrastructure",
        label: "Software - Infrastructure",
        eliteOnly: false
      },
      {
        value: "solar",
        label: "Solar",
        eliteOnly: false
      },
      {
        value: "specialtybusinessservices",
        label: "Specialty Business Services",
        eliteOnly: false
      },
      {
        value: "specialtychemicals",
        label: "Specialty Chemicals",
        eliteOnly: false
      },
      {
        value: "specialtyindustrialmachinery",
        label: "Specialty Industrial Machinery",
        eliteOnly: false
      },
      {
        value: "specialtyretail",
        label: "Specialty Retail",
        eliteOnly: false
      },
      {
        value: "staffingemploymentservices",
        label: "Staffing & Employment Services",
        eliteOnly: false
      },
      {
        value: "steel",
        label: "Steel",
        eliteOnly: false
      },
      {
        value: "stocksonly",
        label: "Stocks only (ex-Funds)",
        eliteOnly: false
      },
      {
        value: "telecomservices",
        label: "Telecom Services",
        eliteOnly: false
      },
      {
        value: "textilemanufacturing",
        label: "Textile Manufacturing",
        eliteOnly: false
      },
      {
        value: "thermalcoal",
        label: "Thermal Coal",
        eliteOnly: false
      },
      {
        value: "tobacco",
        label: "Tobacco",
        eliteOnly: false
      },
      {
        value: "toolsaccessories",
        label: "Tools & Accessories",
        eliteOnly: false
      },
      {
        value: "travelservices",
        label: "Travel Services",
        eliteOnly: false
      },
      {
        value: "trucking",
        label: "Trucking",
        eliteOnly: false
      },
      {
        value: "uranium",
        label: "Uranium",
        eliteOnly: false
      },
      {
        value: "utilitiesdiversified",
        label: "Utilities - Diversified",
        eliteOnly: false
      },
      {
        value: "utilitiesindependentpowerproducers",
        label: "Utilities - Independent Power Producers",
        eliteOnly: false
      },
      {
        value: "utilitiesregulatedelectric",
        label: "Utilities - Regulated Electric",
        eliteOnly: false
      },
      {
        value: "utilitiesregulatedgas",
        label: "Utilities - Regulated Gas",
        eliteOnly: false
      },
      {
        value: "utilitiesregulatedwater",
        label: "Utilities - Regulated Water",
        eliteOnly: false
      },
      {
        value: "utilitiesrenewable",
        label: "Utilities - Renewable",
        eliteOnly: false
      },
      {
        value: "wastemanagement",
        label: "Waste Management",
        eliteOnly: false
      },
      {
        value: "custom_subscription",
        label: "Custom (Elite only)",
        eliteOnly: true
      }
    ]
  },
  ipoDate: {
    key: "ipoDate",
    label: "IPO Date",
    dataFilter: "ipodate",
    groups: [
      "descriptive",
      "all"
    ],
    options: [
      {
        value: "",
        label: "Any",
        eliteOnly: false
      },
      {
        value: "prev2yrs",
        label: "In the last 2 years",
        eliteOnly: false
      },
      {
        value: "prev3yrs",
        label: "In the last 3 years",
        eliteOnly: false
      },
      {
        value: "prev5yrs",
        label: "In the last 5 years",
        eliteOnly: false
      },
      {
        value: "prevmonth",
        label: "In the last month",
        eliteOnly: false
      },
      {
        value: "prevquarter",
        label: "In the last quarter",
        eliteOnly: false
      },
      {
        value: "prevweek",
        label: "In the last week",
        eliteOnly: false
      },
      {
        value: "prevyear",
        label: "In the last year",
        eliteOnly: false
      },
      {
        value: "more10",
        label: "More than 10 years ago",
        eliteOnly: false
      },
      {
        value: "more15",
        label: "More than 15 years ago",
        eliteOnly: false
      },
      {
        value: "more20",
        label: "More than 20 years ago",
        eliteOnly: false
      },
      {
        value: "more25",
        label: "More than 25 years ago",
        eliteOnly: false
      },
      {
        value: "more5",
        label: "More than 5 years ago",
        eliteOnly: false
      },
      {
        value: "more1",
        label: "More than a year ago",
        eliteOnly: false
      },
      {
        value: "today",
        label: "Today",
        eliteOnly: false
      },
      {
        value: "yesterday",
        label: "Yesterday",
        eliteOnly: false
      },
      {
        value: "custom_subscription",
        label: "Custom (Elite only)",
        eliteOnly: true
      }
    ]
  },
  marketCap: {
    key: "marketCap",
    label: "Market Cap.",
    dataFilter: "cap",
    groups: [
      "descriptive",
      "all"
    ],
    options: [
      {
        value: "",
        label: "Any",
        eliteOnly: false
      },
      {
        value: "largeover",
        label: "+Large (over $10bln)",
        eliteOnly: false
      },
      {
        value: "microover",
        label: "+Micro (over $50mln)",
        eliteOnly: false
      },
      {
        value: "midover",
        label: "+Mid (over $2bln)",
        eliteOnly: false
      },
      {
        value: "smallover",
        label: "+Small (over $300mln)",
        eliteOnly: false
      },
      {
        value: "largeunder",
        label: "-Large (under $200bln)",
        eliteOnly: false
      },
      {
        value: "microunder",
        label: "-Micro (under $300mln)",
        eliteOnly: false
      },
      {
        value: "midunder",
        label: "-Mid (under $10bln)",
        eliteOnly: false
      },
      {
        value: "smallunder",
        label: "-Small (under $2bln)",
        eliteOnly: false
      },
      {
        value: "large",
        label: "Large ($10bln to $200bln)",
        eliteOnly: false
      },
      {
        value: "mega",
        label: "Mega ($200bln and more)",
        eliteOnly: false
      },
      {
        value: "micro",
        label: "Micro ($50mln to $300mln)",
        eliteOnly: false
      },
      {
        value: "mid",
        label: "Mid ($2bln to $10bln)",
        eliteOnly: false
      },
      {
        value: "nano",
        label: "Nano (under $50mln)",
        eliteOnly: false
      },
      {
        value: "small",
        label: "Small ($300mln to $2bln)",
        eliteOnly: false
      },
      {
        value: "custom_subscription",
        label: "Custom (Elite only)",
        eliteOnly: true
      }
    ]
  },
  news_date: {
    key: "news_date",
    label: "Latest News",
    dataFilter: "news_date",
    groups: [
      "all",
      "news"
    ],
    options: [
      {
        value: "",
        label: "Any",
        eliteOnly: false
      },
      {
        value: "todayafter",
        label: "Aftermarket Today",
        eliteOnly: false
      },
      {
        value: "yesterdayafter",
        label: "In the Aftermarket Yesterday",
        eliteOnly: false
      },
      {
        value: "prevhours24",
        label: "In the last 24 hours",
        eliteOnly: false
      },
      {
        value: "prevminutes30",
        label: "In the last 30 minutes",
        eliteOnly: false
      },
      {
        value: "prevminutes5",
        label: "In the last 5 minutes",
        eliteOnly: false
      },
      {
        value: "prevdays7",
        label: "In the last 7 days",
        eliteOnly: false
      },
      {
        value: "prevhours1",
        label: "In the last hour",
        eliteOnly: false
      },
      {
        value: "prevmonth",
        label: "In the last month",
        eliteOnly: false
      },
      {
        value: "sinceyesterday",
        label: "Since Yesterday",
        eliteOnly: false
      },
      {
        value: "sinceyesterdayafter",
        label: "Since the Aftermarket Yesterday",
        eliteOnly: false
      },
      {
        value: "today",
        label: "Today",
        eliteOnly: false
      },
      {
        value: "yesterday",
        label: "Yesterday",
        eliteOnly: false
      },
      {
        value: "custom_subscription",
        label: "Custom (Elite only)",
        eliteOnly: true
      }
    ]
  },
  optionShort: {
    key: "optionShort",
    label: "Option/Short",
    dataFilter: "sh_opt",
    groups: [
      "descriptive",
      "all"
    ],
    options: [
      {
        value: "",
        label: "Any",
        eliteOnly: false
      },
      {
        value: "notoption",
        label: "Not optionable",
        eliteOnly: false
      },
      {
        value: "notoptionnotshort",
        label: "Not optionable and not shortable",
        eliteOnly: false
      },
      {
        value: "notoptionshort",
        label: "Not optionable and shortable",
        eliteOnly: false
      },
      {
        value: "notshort",
        label: "Not shortable",
        eliteOnly: false
      },
      {
        value: "option",
        label: "Optionable",
        eliteOnly: false
      },
      {
        value: "optionnotshort",
        label: "Optionable and not shortable",
        eliteOnly: false
      },
      {
        value: "optionshort",
        label: "Optionable and shortable",
        eliteOnly: false
      },
      {
        value: "uo100m",
        label: "Over $100M available to short",
        eliteOnly: false
      },
      {
        value: "uo10m",
        label: "Over $10M available to short",
        eliteOnly: false
      },
      {
        value: "uo1b",
        label: "Over $1B available to short",
        eliteOnly: false
      },
      {
        value: "uo1m",
        label: "Over $1M available to short",
        eliteOnly: false
      },
      {
        value: "so100k",
        label: "Over 100K available to short",
        eliteOnly: false
      },
      {
        value: "so10k",
        label: "Over 10K available to short",
        eliteOnly: false
      },
      {
        value: "so10m",
        label: "Over 10M available to short",
        eliteOnly: false
      },
      {
        value: "so1m",
        label: "Over 1M available to short",
        eliteOnly: false
      },
      {
        value: "restricted",
        label: "Short Sale Restricted (Elite only)",
        eliteOnly: true
      },
      {
        value: "short",
        label: "Shortable",
        eliteOnly: false
      },
      {
        value: "custom_subscription",
        label: "Custom (Elite only)",
        eliteOnly: true
      }
    ]
  },
  priceBand: {
    key: "priceBand",
    label: "Price $",
    dataFilter: "sh_price",
    groups: [
      "descriptive",
      "all"
    ],
    options: [
      {
        value: "",
        label: "Any",
        eliteOnly: false
      },
      {
        value: "1to10",
        label: "$1 to $10",
        eliteOnly: false
      },
      {
        value: "1to20",
        label: "$1 to $20",
        eliteOnly: false
      },
      {
        value: "1to5",
        label: "$1 to $5",
        eliteOnly: false
      },
      {
        value: "10to20",
        label: "$10 to $20",
        eliteOnly: false
      },
      {
        value: "10to50",
        label: "$10 to $50",
        eliteOnly: false
      },
      {
        value: "20to50",
        label: "$20 to $50",
        eliteOnly: false
      },
      {
        value: "5to10",
        label: "$5 to $10",
        eliteOnly: false
      },
      {
        value: "5to20",
        label: "$5 to $20",
        eliteOnly: false
      },
      {
        value: "5to50",
        label: "$5 to $50",
        eliteOnly: false
      },
      {
        value: "50to100",
        label: "$50 to $100",
        eliteOnly: false
      },
      {
        value: "add_tad_0_close::close:d",
        label: "Custom TA",
        eliteOnly: false
      },
      {
        value: "o1",
        label: "Over $1",
        eliteOnly: false
      },
      {
        value: "o10",
        label: "Over $10",
        eliteOnly: false
      },
      {
        value: "o100",
        label: "Over $100",
        eliteOnly: false
      },
      {
        value: "o15",
        label: "Over $15",
        eliteOnly: false
      },
      {
        value: "o2",
        label: "Over $2",
        eliteOnly: false
      },
      {
        value: "o20",
        label: "Over $20",
        eliteOnly: false
      },
      {
        value: "o3",
        label: "Over $3",
        eliteOnly: false
      },
      {
        value: "o30",
        label: "Over $30",
        eliteOnly: false
      },
      {
        value: "o4",
        label: "Over $4",
        eliteOnly: false
      },
      {
        value: "o40",
        label: "Over $40",
        eliteOnly: false
      },
      {
        value: "o5",
        label: "Over $5",
        eliteOnly: false
      },
      {
        value: "o50",
        label: "Over $50",
        eliteOnly: false
      },
      {
        value: "o60",
        label: "Over $60",
        eliteOnly: false
      },
      {
        value: "o7",
        label: "Over $7",
        eliteOnly: false
      },
      {
        value: "o70",
        label: "Over $70",
        eliteOnly: false
      },
      {
        value: "o80",
        label: "Over $80",
        eliteOnly: false
      },
      {
        value: "o90",
        label: "Over $90",
        eliteOnly: false
      },
      {
        value: "u1",
        label: "Under $1",
        eliteOnly: false
      },
      {
        value: "u10",
        label: "Under $10",
        eliteOnly: false
      },
      {
        value: "u15",
        label: "Under $15",
        eliteOnly: false
      },
      {
        value: "u2",
        label: "Under $2",
        eliteOnly: false
      },
      {
        value: "u20",
        label: "Under $20",
        eliteOnly: false
      },
      {
        value: "u3",
        label: "Under $3",
        eliteOnly: false
      },
      {
        value: "u30",
        label: "Under $30",
        eliteOnly: false
      },
      {
        value: "u4",
        label: "Under $4",
        eliteOnly: false
      },
      {
        value: "u40",
        label: "Under $40",
        eliteOnly: false
      },
      {
        value: "u5",
        label: "Under $5",
        eliteOnly: false
      },
      {
        value: "u50",
        label: "Under $50",
        eliteOnly: false
      },
      {
        value: "u7",
        label: "Under $7",
        eliteOnly: false
      },
      {
        value: "custom_subscription",
        label: "Custom (Elite only)",
        eliteOnly: true
      }
    ]
  },
  relVolume: {
    key: "relVolume",
    label: "Relative Volume",
    dataFilter: "sh_relvol",
    groups: [
      "descriptive",
      "all"
    ],
    options: [
      {
        value: "",
        label: "Any",
        eliteOnly: false
      },
      {
        value: "o0.25",
        label: "Over 0.25",
        eliteOnly: false
      },
      {
        value: "o0.5",
        label: "Over 0.5",
        eliteOnly: false
      },
      {
        value: "o0.75",
        label: "Over 0.75",
        eliteOnly: false
      },
      {
        value: "o1",
        label: "Over 1",
        eliteOnly: false
      },
      {
        value: "o1.5",
        label: "Over 1.5",
        eliteOnly: false
      },
      {
        value: "o10",
        label: "Over 10",
        eliteOnly: false
      },
      {
        value: "o2",
        label: "Over 2",
        eliteOnly: false
      },
      {
        value: "o3",
        label: "Over 3",
        eliteOnly: false
      },
      {
        value: "o5",
        label: "Over 5",
        eliteOnly: false
      },
      {
        value: "u0.1",
        label: "Under 0.1",
        eliteOnly: false
      },
      {
        value: "u0.25",
        label: "Under 0.25",
        eliteOnly: false
      },
      {
        value: "u0.5",
        label: "Under 0.5",
        eliteOnly: false
      },
      {
        value: "u0.75",
        label: "Under 0.75",
        eliteOnly: false
      },
      {
        value: "u1",
        label: "Under 1",
        eliteOnly: false
      },
      {
        value: "u1.5",
        label: "Under 1.5",
        eliteOnly: false
      },
      {
        value: "u2",
        label: "Under 2",
        eliteOnly: false
      },
      {
        value: "custom_subscription",
        label: "Custom (Elite only)",
        eliteOnly: true
      }
    ]
  },
  sector: {
    key: "sector",
    label: "Sector",
    dataFilter: "sec",
    groups: [
      "descriptive",
      "all"
    ],
    options: [
      {
        value: "",
        label: "Any",
        eliteOnly: false
      },
      {
        value: "basicmaterials",
        label: "Basic Materials",
        eliteOnly: false
      },
      {
        value: "communicationservices",
        label: "Communication Services",
        eliteOnly: false
      },
      {
        value: "consumercyclical",
        label: "Consumer Cyclical",
        eliteOnly: false
      },
      {
        value: "consumerdefensive",
        label: "Consumer Defensive",
        eliteOnly: false
      },
      {
        value: "energy",
        label: "Energy",
        eliteOnly: false
      },
      {
        value: "financial",
        label: "Financial",
        eliteOnly: false
      },
      {
        value: "healthcare",
        label: "Healthcare",
        eliteOnly: false
      },
      {
        value: "industrials",
        label: "Industrials",
        eliteOnly: false
      },
      {
        value: "realestate",
        label: "Real Estate",
        eliteOnly: false
      },
      {
        value: "technology",
        label: "Technology",
        eliteOnly: false
      },
      {
        value: "utilities",
        label: "Utilities",
        eliteOnly: false
      },
      {
        value: "custom_subscription",
        label: "Custom (Elite only)",
        eliteOnly: true
      }
    ]
  },
  sh_insiderown: {
    key: "sh_insiderown",
    label: "Insider Ownership",
    dataFilter: "sh_insiderown",
    groups: [
      "fundamental",
      "all"
    ],
    options: [
      {
        value: "",
        label: "Any",
        eliteOnly: false
      },
      {
        value: "high",
        label: "High (>30%)",
        eliteOnly: false
      },
      {
        value: "low",
        label: "Low (<5%)",
        eliteOnly: false
      },
      {
        value: "o10",
        label: "Over 10%",
        eliteOnly: false
      },
      {
        value: "o20",
        label: "Over 20%",
        eliteOnly: false
      },
      {
        value: "o30",
        label: "Over 30%",
        eliteOnly: false
      },
      {
        value: "o40",
        label: "Over 40%",
        eliteOnly: false
      },
      {
        value: "o50",
        label: "Over 50%",
        eliteOnly: false
      },
      {
        value: "o60",
        label: "Over 60%",
        eliteOnly: false
      },
      {
        value: "o70",
        label: "Over 70%",
        eliteOnly: false
      },
      {
        value: "o80",
        label: "Over 80%",
        eliteOnly: false
      },
      {
        value: "o90",
        label: "Over 90%",
        eliteOnly: false
      },
      {
        value: "veryhigh",
        label: "Very High (>50%)",
        eliteOnly: false
      },
      {
        value: "custom_subscription",
        label: "Custom (Elite only)",
        eliteOnly: true
      }
    ]
  },
  sh_insidertrans: {
    key: "sh_insidertrans",
    label: "Insider Transactions",
    dataFilter: "sh_insidertrans",
    groups: [
      "fundamental",
      "all"
    ],
    options: [
      {
        value: "",
        label: "Any",
        eliteOnly: false
      },
      {
        value: "neg",
        label: "Negative (<0%)",
        eliteOnly: false
      },
      {
        value: "o10",
        label: "Over +10%",
        eliteOnly: false
      },
      {
        value: "o15",
        label: "Over +15%",
        eliteOnly: false
      },
      {
        value: "o20",
        label: "Over +20%",
        eliteOnly: false
      },
      {
        value: "o25",
        label: "Over +25%",
        eliteOnly: false
      },
      {
        value: "o30",
        label: "Over +30%",
        eliteOnly: false
      },
      {
        value: "o35",
        label: "Over +35%",
        eliteOnly: false
      },
      {
        value: "o40",
        label: "Over +40%",
        eliteOnly: false
      },
      {
        value: "o45",
        label: "Over +45%",
        eliteOnly: false
      },
      {
        value: "o5",
        label: "Over +5%",
        eliteOnly: false
      },
      {
        value: "o50",
        label: "Over +50%",
        eliteOnly: false
      },
      {
        value: "o60",
        label: "Over +60%",
        eliteOnly: false
      },
      {
        value: "o70",
        label: "Over +70%",
        eliteOnly: false
      },
      {
        value: "o80",
        label: "Over +80%",
        eliteOnly: false
      },
      {
        value: "o90",
        label: "Over +90%",
        eliteOnly: false
      },
      {
        value: "pos",
        label: "Positive (>0%)",
        eliteOnly: false
      },
      {
        value: "u-10",
        label: "Under -10%",
        eliteOnly: false
      },
      {
        value: "u-15",
        label: "Under -15%",
        eliteOnly: false
      },
      {
        value: "u-20",
        label: "Under -20%",
        eliteOnly: false
      },
      {
        value: "u-25",
        label: "Under -25%",
        eliteOnly: false
      },
      {
        value: "u-30",
        label: "Under -30%",
        eliteOnly: false
      },
      {
        value: "u-35",
        label: "Under -35%",
        eliteOnly: false
      },
      {
        value: "u-40",
        label: "Under -40%",
        eliteOnly: false
      },
      {
        value: "u-45",
        label: "Under -45%",
        eliteOnly: false
      },
      {
        value: "u-5",
        label: "Under -5%",
        eliteOnly: false
      },
      {
        value: "u-50",
        label: "Under -50%",
        eliteOnly: false
      },
      {
        value: "u-60",
        label: "Under -60%",
        eliteOnly: false
      },
      {
        value: "u-70",
        label: "Under -70%",
        eliteOnly: false
      },
      {
        value: "u-80",
        label: "Under -80%",
        eliteOnly: false
      },
      {
        value: "u-90",
        label: "Under -90%",
        eliteOnly: false
      },
      {
        value: "veryneg",
        label: "Very Negative (<20%)",
        eliteOnly: false
      },
      {
        value: "verypos",
        label: "Very Positive (>20%)",
        eliteOnly: false
      },
      {
        value: "custom_subscription",
        label: "Custom (Elite only)",
        eliteOnly: true
      }
    ]
  },
  sh_instown: {
    key: "sh_instown",
    label: "Institutional Ownership",
    dataFilter: "sh_instown",
    groups: [
      "fundamental",
      "all"
    ],
    options: [
      {
        value: "",
        label: "Any",
        eliteOnly: false
      },
      {
        value: "high",
        label: "High (>90%)",
        eliteOnly: false
      },
      {
        value: "low",
        label: "Low (<5%)",
        eliteOnly: false
      },
      {
        value: "o10",
        label: "Over 10%",
        eliteOnly: false
      },
      {
        value: "o20",
        label: "Over 20%",
        eliteOnly: false
      },
      {
        value: "o30",
        label: "Over 30%",
        eliteOnly: false
      },
      {
        value: "o40",
        label: "Over 40%",
        eliteOnly: false
      },
      {
        value: "o50",
        label: "Over 50%",
        eliteOnly: false
      },
      {
        value: "o60",
        label: "Over 60%",
        eliteOnly: false
      },
      {
        value: "o70",
        label: "Over 70%",
        eliteOnly: false
      },
      {
        value: "o80",
        label: "Over 80%",
        eliteOnly: false
      },
      {
        value: "o90",
        label: "Over 90%",
        eliteOnly: false
      },
      {
        value: "u10",
        label: "Under 10%",
        eliteOnly: false
      },
      {
        value: "u20",
        label: "Under 20%",
        eliteOnly: false
      },
      {
        value: "u30",
        label: "Under 30%",
        eliteOnly: false
      },
      {
        value: "u40",
        label: "Under 40%",
        eliteOnly: false
      },
      {
        value: "u50",
        label: "Under 50%",
        eliteOnly: false
      },
      {
        value: "u60",
        label: "Under 60%",
        eliteOnly: false
      },
      {
        value: "u70",
        label: "Under 70%",
        eliteOnly: false
      },
      {
        value: "u80",
        label: "Under 80%",
        eliteOnly: false
      },
      {
        value: "u90",
        label: "Under 90%",
        eliteOnly: false
      },
      {
        value: "custom_subscription",
        label: "Custom (Elite only)",
        eliteOnly: true
      }
    ]
  },
  sh_insttrans: {
    key: "sh_insttrans",
    label: "Institutional Transactions",
    dataFilter: "sh_insttrans",
    groups: [
      "fundamental",
      "all"
    ],
    options: [
      {
        value: "",
        label: "Any",
        eliteOnly: false
      },
      {
        value: "neg",
        label: "Negative (<0%)",
        eliteOnly: false
      },
      {
        value: "o10",
        label: "Over +10%",
        eliteOnly: false
      },
      {
        value: "o15",
        label: "Over +15%",
        eliteOnly: false
      },
      {
        value: "o20",
        label: "Over +20%",
        eliteOnly: false
      },
      {
        value: "o25",
        label: "Over +25%",
        eliteOnly: false
      },
      {
        value: "o30",
        label: "Over +30%",
        eliteOnly: false
      },
      {
        value: "o35",
        label: "Over +35%",
        eliteOnly: false
      },
      {
        value: "o40",
        label: "Over +40%",
        eliteOnly: false
      },
      {
        value: "o45",
        label: "Over +45%",
        eliteOnly: false
      },
      {
        value: "o5",
        label: "Over +5%",
        eliteOnly: false
      },
      {
        value: "o50",
        label: "Over +50%",
        eliteOnly: false
      },
      {
        value: "pos",
        label: "Positive (>0%)",
        eliteOnly: false
      },
      {
        value: "u-10",
        label: "Under -10%",
        eliteOnly: false
      },
      {
        value: "u-15",
        label: "Under -15%",
        eliteOnly: false
      },
      {
        value: "u-20",
        label: "Under -20%",
        eliteOnly: false
      },
      {
        value: "u-25",
        label: "Under -25%",
        eliteOnly: false
      },
      {
        value: "u-30",
        label: "Under -30%",
        eliteOnly: false
      },
      {
        value: "u-35",
        label: "Under -35%",
        eliteOnly: false
      },
      {
        value: "u-40",
        label: "Under -40%",
        eliteOnly: false
      },
      {
        value: "u-45",
        label: "Under -45%",
        eliteOnly: false
      },
      {
        value: "u-5",
        label: "Under -5%",
        eliteOnly: false
      },
      {
        value: "u-50",
        label: "Under -50%",
        eliteOnly: false
      },
      {
        value: "veryneg",
        label: "Very Negative (<20%)",
        eliteOnly: false
      },
      {
        value: "verypos",
        label: "Very Positive (>20%)",
        eliteOnly: false
      },
      {
        value: "custom_subscription",
        label: "Custom (Elite only)",
        eliteOnly: true
      }
    ]
  },
  sharesOutstanding: {
    key: "sharesOutstanding",
    label: "Shares Outstanding",
    dataFilter: "sh_outstanding",
    groups: [
      "descriptive",
      "all"
    ],
    options: [
      {
        value: "",
        label: "Any",
        eliteOnly: false
      },
      {
        value: "o1000",
        label: "Over 1000M",
        eliteOnly: false
      },
      {
        value: "o100",
        label: "Over 100M",
        eliteOnly: false
      },
      {
        value: "o10",
        label: "Over 10M",
        eliteOnly: false
      },
      {
        value: "o1",
        label: "Over 1M",
        eliteOnly: false
      },
      {
        value: "o200",
        label: "Over 200M",
        eliteOnly: false
      },
      {
        value: "o20",
        label: "Over 20M",
        eliteOnly: false
      },
      {
        value: "o2",
        label: "Over 2M",
        eliteOnly: false
      },
      {
        value: "o500",
        label: "Over 500M",
        eliteOnly: false
      },
      {
        value: "o50",
        label: "Over 50M",
        eliteOnly: false
      },
      {
        value: "o5",
        label: "Over 5M",
        eliteOnly: false
      },
      {
        value: "u100",
        label: "Under 100M",
        eliteOnly: false
      },
      {
        value: "u10",
        label: "Under 10M",
        eliteOnly: false
      },
      {
        value: "u1",
        label: "Under 1M",
        eliteOnly: false
      },
      {
        value: "u20",
        label: "Under 20M",
        eliteOnly: false
      },
      {
        value: "u50",
        label: "Under 50M",
        eliteOnly: false
      },
      {
        value: "u5",
        label: "Under 5M",
        eliteOnly: false
      },
      {
        value: "custom_subscription",
        label: "Custom (Elite only)",
        eliteOnly: true
      }
    ]
  },
  shortFloat: {
    key: "shortFloat",
    label: "Short Float",
    dataFilter: "sh_short",
    groups: [
      "descriptive",
      "all"
    ],
    options: [
      {
        value: "",
        label: "Any",
        eliteOnly: false
      },
      {
        value: "high",
        label: "High (>20%)",
        eliteOnly: false
      },
      {
        value: "low",
        label: "Low (<5%)",
        eliteOnly: false
      },
      {
        value: "o10",
        label: "Over 10%",
        eliteOnly: false
      },
      {
        value: "o15",
        label: "Over 15%",
        eliteOnly: false
      },
      {
        value: "o20",
        label: "Over 20%",
        eliteOnly: false
      },
      {
        value: "o25",
        label: "Over 25%",
        eliteOnly: false
      },
      {
        value: "o30",
        label: "Over 30%",
        eliteOnly: false
      },
      {
        value: "o5",
        label: "Over 5%",
        eliteOnly: false
      },
      {
        value: "u10",
        label: "Under 10%",
        eliteOnly: false
      },
      {
        value: "u15",
        label: "Under 15%",
        eliteOnly: false
      },
      {
        value: "u20",
        label: "Under 20%",
        eliteOnly: false
      },
      {
        value: "u25",
        label: "Under 25%",
        eliteOnly: false
      },
      {
        value: "u30",
        label: "Under 30%",
        eliteOnly: false
      },
      {
        value: "u5",
        label: "Under 5%",
        eliteOnly: false
      },
      {
        value: "custom_subscription",
        label: "Custom (Elite only)",
        eliteOnly: true
      }
    ]
  },
  subTheme: {
    key: "subTheme",
    label: "Sub-theme",
    dataFilter: "subtheme",
    groups: [
      "descriptive",
      "all"
    ],
    options: [
      {
        value: "",
        label: "Any",
        eliteOnly: false
      },
      {
        value: "aiagi",
        label: "AI - AGI, general intelligence",
        eliteOnly: false
      },
      {
        value: "aiadssearch",
        label: "AI - Ads, Search & Recommendations",
        eliteOnly: false
      },
      {
        value: "aiapplications",
        label: "AI - Apps, Domain-Specific AI",
        eliteOnly: false
      },
      {
        value: "aicloud",
        label: "AI - Cloud & Infrastructure",
        eliteOnly: false
      },
      {
        value: "aicompute",
        label: "AI - Compute & Acceleration",
        eliteOnly: false
      },
      {
        value: "aisecurity",
        label: "AI - Cybersecurity",
        eliteOnly: false
      },
      {
        value: "aidata",
        label: "AI - Data Infrastructure & Enablement",
        eliteOnly: false
      },
      {
        value: "aiedge",
        label: "AI - Edge & Embedded Systems",
        eliteOnly: false
      },
      {
        value: "aienterprise",
        label: "AI - Enterprise Productivity & Software Integration",
        eliteOnly: false
      },
      {
        value: "aimodels",
        label: "AI - Foundation Models & Platforms",
        eliteOnly: false
      },
      {
        value: "ainetworking",
        label: "AI - Networking & Systems Optimization",
        eliteOnly: false
      },
      {
        value: "aienergy",
        label: "AI - Power & Energy Solutions",
        eliteOnly: false
      },
      {
        value: "airobotics",
        label: "AI - Robotics & Automation",
        eliteOnly: false
      },
      {
        value: "agricultureprocessing",
        label: "Agriculture - Agri-Food Processing & Distribution",
        eliteOnly: false
      },
      {
        value: "agriculturecropinputs",
        label: "Agriculture - Agricultural Inputs & Crop Science",
        eliteOnly: false
      },
      {
        value: "agriculturealtprotein",
        label: "Agriculture - Alternative Proteins",
        eliteOnly: false
      },
      {
        value: "agricultureindoorfarming",
        label: "Agriculture - Controlled Environment Agriculture",
        eliteOnly: false
      },
      {
        value: "agriculturesmartfarming",
        label: "Agriculture - Precision Agriculture & Farm Automation",
        eliteOnly: false
      },
      {
        value: "automationdprinting",
        label: "Automation - Additive Manufacturing, 3D Printing",
        eliteOnly: false
      },
      {
        value: "automationautomation",
        label: "Automation - Factory & Process Automation Systems",
        eliteOnly: false
      },
      {
        value: "automationiot",
        label: "Automation - Industrial IoT, Connectivity",
        eliteOnly: false
      },
      {
        value: "automationrobotics",
        label: "Automation - Industrial Robotics & Autonomous Systems",
        eliteOnly: false
      },
      {
        value: "automationmachinevision",
        label: "Automation - Industrial Sensors & Machine Vision",
        eliteOnly: false
      },
      {
        value: "automationsoftware",
        label: "Automation - Industrial Software & Digital Twin",
        eliteOnly: false
      },
      {
        value: "automationlogistics",
        label: "Automation - Smart Logistics & Warehouse Automation",
        eliteOnly: false
      },
      {
        value: "autonomousdefense",
        label: "Autonomous  - Aerospace, Defense & Drones",
        eliteOnly: false
      },
      {
        value: "autonomousindustrial",
        label: "Autonomous  - Industrial & Logistics Automation",
        eliteOnly: false
      },
      {
        value: "autonomousspecialized",
        label: "Autonomous  - Maritime, Agriculture & Specialized Autonomy",
        eliteOnly: false
      },
      {
        value: "autonomousmachinevision",
        label: "Autonomous  - Sensors & Perception Systems",
        eliteOnly: false
      },
      {
        value: "autonomoussoftware",
        label: "Autonomous  - Software & Cloud Infrastructure",
        eliteOnly: false
      },
      {
        value: "autonomousavmobility",
        label: "Autonomous  - Vehicles & Mobility",
        eliteOnly: false
      },
      {
        value: "bigdataaiplatforms",
        label: "Big Data - AI Platforms & Predictive Analytics",
        eliteOnly: false
      },
      {
        value: "bigdataanalyticsbi",
        label: "Big Data - Analytics & Business Intelligence",
        eliteOnly: false
      },
      {
        value: "bigdataproviders",
        label: "Big Data - Data Generation, Sourcing & Providers",
        eliteOnly: false
      },
      {
        value: "bigdatainfrastructure",
        label: "Big Data - Infrastructure & Storage",
        eliteOnly: false
      },
      {
        value: "biometricshardware",
        label: "Biometrics - Biometric Sensors & Hardware",
        eliteOnly: false
      },
      {
        value: "biometricsgovdefense",
        label: "Biometrics - Government, Defense & Public Security",
        eliteOnly: false
      },
      {
        value: "biometricsidentity",
        label: "Biometrics - Identity Verification & Security",
        eliteOnly: false
      },
      {
        value: "biometricssoftware",
        label: "Biometrics - Recognition & Analytics",
        eliteOnly: false
      },
      {
        value: "blockchaininfrastructure",
        label: "Blockchain - Blockchain Infrastructure",
        eliteOnly: false
      },
      {
        value: "blockchainmining",
        label: "Blockchain - Cryptocurrency Mining & Staking",
        eliteOnly: false
      },
      {
        value: "blockchainplatforms",
        label: "Blockchain - Cryptocurrency Platforms",
        eliteOnly: false
      },
      {
        value: "blockchainenterprise",
        label: "Blockchain - Enterprise Blockchain Solutions",
        eliteOnly: false
      },
      {
        value: "blockchainpayments",
        label: "Blockchain - Financial Services & Payments",
        eliteOnly: false
      },
      {
        value: "blockchaintokenization",
        label: "Blockchain - Tokenization & Digital Assets",
        eliteOnly: false
      },
      {
        value: "clouddatacenters",
        label: "Cloud - Data Centers",
        eliteOnly: false
      },
      {
        value: "clouddatabases",
        label: "Cloud - Data Platforms & Databases",
        eliteOnly: false
      },
      {
        value: "clouddevops",
        label: "Cloud - DevOps, Observability",
        eliteOnly: false
      },
      {
        value: "cloudedge",
        label: "Cloud - Edge, CDN, Zero-Trust Networking",
        eliteOnly: false
      },
      {
        value: "cloudhardware",
        label: "Cloud - Hardware, Networking & OEM",
        eliteOnly: false
      },
      {
        value: "cloudhsaas",
        label: "Cloud - Horizontal SaaS & Cloud Applications",
        eliteOnly: false
      },
      {
        value: "cloudhybridcloud",
        label: "Cloud - Hybrid Cloud",
        eliteOnly: false
      },
      {
        value: "cloudhyperscalers",
        label: "Cloud - Hyperscalers",
        eliteOnly: false
      },
      {
        value: "cloudmulticloud",
        label: "Cloud - Multi-Cloud Management",
        eliteOnly: false
      },
      {
        value: "cloudpaas",
        label: "Cloud - Platforms & Services, PaaS",
        eliteOnly: false
      },
      {
        value: "cloudsecurity",
        label: "Cloud - Security",
        eliteOnly: false
      },
      {
        value: "cloudserverless",
        label: "Cloud - Serverless Computing",
        eliteOnly: false
      },
      {
        value: "commagrifertilizers",
        label: "Comm Agri - Fertilizers, Crop Inputs & Seeds",
        eliteOnly: false
      },
      {
        value: "commagrigrains",
        label: "Comm Agri - Grains & Oilseeds",
        eliteOnly: false
      },
      {
        value: "commagrilivestock",
        label: "Comm Agri - Livestock & Animal Protein",
        eliteOnly: false
      },
      {
        value: "commagribiofuels",
        label: "Comm Agri - Renewable Fuels & Biofuels",
        eliteOnly: false
      },
      {
        value: "commagrisofts",
        label: "Comm Agri - Softs & Plantation Crops",
        eliteOnly: false
      },
      {
        value: "commenergybiofuels",
        label: "Comm Energy - Biofuels & Renewable Fuels",
        eliteOnly: false
      },
      {
        value: "commenergyoil",
        label: "Comm Energy - Crude Oil",
        eliteOnly: false
      },
      {
        value: "commenergygaslng",
        label: "Comm Energy - Natural Gas & LNG",
        eliteOnly: false
      },
      {
        value: "commenergyuranium",
        label: "Comm Energy - Uranium & Nuclear Fuels",
        eliteOnly: false
      },
      {
        value: "commmetalsbattery",
        label: "Comm Metals - Battery & Energy Transition Metals",
        eliteOnly: false
      },
      {
        value: "commmetalsgold",
        label: "Comm Metals - Gold",
        eliteOnly: false
      },
      {
        value: "commmetalsindustrial",
        label: "Comm Metals - Industrial & Base Metals",
        eliteOnly: false
      },
      {
        value: "commmetalsprecious",
        label: "Comm Metals - Precious Metals",
        eliteOnly: false
      },
      {
        value: "commmetalsrareearth",
        label: "Comm Metals - Rare Earth & Strategic Materials",
        eliteOnly: false
      },
      {
        value: "commmetalsrecycling",
        label: "Comm Metals - Recycling & Circular Materials",
        eliteOnly: false
      },
      {
        value: "commmetalssilver",
        label: "Comm Metals - Silver",
        eliteOnly: false
      },
      {
        value: "consumerapparel",
        label: "Consumer - Apparel & E-Commerce Retail",
        eliteOnly: false
      },
      {
        value: "consumerfarmdirect",
        label: "Consumer - Farming & Direct Marketplaces",
        eliteOnly: false
      },
      {
        value: "consumerfood",
        label: "Consumer - Health, Food & Beverages",
        eliteOnly: false
      },
      {
        value: "consumerluxury",
        label: "Consumer - Modern Luxury & Lifestyle",
        eliteOnly: false
      },
      {
        value: "consumersecondhand",
        label: "Consumer - Resale & Sharing Platforms",
        eliteOnly: false
      },
      {
        value: "consumerhousehold",
        label: "Consumer - Smart Homes & Household Products",
        eliteOnly: false
      },
      {
        value: "cybersecurityappsecurity",
        label: "Cybersecurity - Application Security",
        eliteOnly: false
      },
      {
        value: "cybersecuritycloud",
        label: "Cybersecurity - Cloud Security",
        eliteOnly: false
      },
      {
        value: "cybersecurityendpoint",
        label: "Cybersecurity - Endpoint Security",
        eliteOnly: false
      },
      {
        value: "cybersecurityidentityiam",
        label: "Cybersecurity - Identity & Access Management",
        eliteOnly: false
      },
      {
        value: "cybersecuritynetwork",
        label: "Cybersecurity - Network Security",
        eliteOnly: false
      },
      {
        value: "cybersecuritysiem",
        label: "Cybersecurity - Security Information & Event Management",
        eliteOnly: false
      },
      {
        value: "cybersecuritythreatops",
        label: "Cybersecurity - Threat Intelligence",
        eliteOnly: false
      },
      {
        value: "cybersecurityzerotrust",
        label: "Cybersecurity - Zero Trust",
        eliteOnly: false
      },
      {
        value: "defensecyberdefense",
        label: "Defense - Cyber Defense & Electronic Warfare",
        eliteOnly: false
      },
      {
        value: "defensedrones",
        label: "Defense - Drones & Anti-Drone Systems",
        eliteOnly: false
      },
      {
        value: "defensemissiles",
        label: "Defense - Missile Defense & Long-Range Weapons",
        eliteOnly: false
      },
      {
        value: "defenseaviation",
        label: "Defense - Next-Generation Aircraft & Maintenance",
        eliteOnly: false
      },
      {
        value: "defenseweapons",
        label: "Defense - Precision Weapons & Ammunition Resupply",
        eliteOnly: false
      },
      {
        value: "defensemanufacturing",
        label: "Defense - Secure Defense Supply Chains",
        eliteOnly: false
      },
      {
        value: "defensespacetech",
        label: "Defense - Space Technology & Satellite Services",
        eliteOnly: false
      },
      {
        value: "ecommercedtc",
        label: "E-commerce - Direct-to-Consumer",
        eliteOnly: false
      },
      {
        value: "ecommercegrocery",
        label: "E-commerce - Grocery & Local Commerce Platforms",
        eliteOnly: false
      },
      {
        value: "ecommercelogistics",
        label: "E-commerce - Logistics & Delivery",
        eliteOnly: false
      },
      {
        value: "ecommerceomnichannel",
        label: "E-commerce - Omnichannel Retailers, Online & Physical Stores",
        eliteOnly: false
      },
      {
        value: "ecommercemarketplaces",
        label: "E-commerce - Online Marketplaces",
        eliteOnly: false
      },
      {
        value: "ecommerceplatforms",
        label: "E-commerce - Platforms",
        eliteOnly: false
      },
      {
        value: "ecommercesecondhand",
        label: "E-commerce - Recommerce, Secondhand Marketplaces",
        eliteOnly: false
      },
      {
        value: "ecommerceadsmedia",
        label: "E-commerce - Retail Media & Advertising",
        eliteOnly: false
      },
      {
        value: "ecommercesocial",
        label: "E-commerce - Social & Influencer Commerce",
        eliteOnly: false
      },
      {
        value: "evschips",
        label: "EVs - Auto Semiconductors & Power Electronics",
        eliteOnly: false
      },
      {
        value: "evsselfdriving",
        label: "EVs - Autonomous Driving",
        eliteOnly: false
      },
      {
        value: "evsbatteries",
        label: "EVs - Batteries & Materials",
        eliteOnly: false
      },
      {
        value: "evscharging",
        label: "EVs - Charging & Infrastructure",
        eliteOnly: false
      },
      {
        value: "evsfleets",
        label: "EVs - Fleet Management & Telematics",
        eliteOnly: false
      },
      {
        value: "evssuppliers",
        label: "EVs - Key Suppliers & Autonomy Tech",
        eliteOnly: false
      },
      {
        value: "evsmanufacturers",
        label: "EVs - Manufacturers",
        eliteOnly: false
      },
      {
        value: "educationcurriculum",
        label: "Education - Digital Curriculum",
        eliteOnly: false
      },
      {
        value: "educationinfrastructure",
        label: "Education - Infrastructure",
        eliteOnly: false
      },
      {
        value: "educationplatforms",
        label: "Education - Online Learning Platforms",
        eliteOnly: false
      },
      {
        value: "educationworkforce",
        label: "Education - Workforce Training",
        eliteOnly: false
      },
      {
        value: "energybasethermal",
        label: "Energy Base - Coal & Thermal Power Generation",
        eliteOnly: false
      },
      {
        value: "energybasemajors",
        label: "Energy Base - Integrated Energy Majors",
        eliteOnly: false
      },
      {
        value: "energybasenuclear",
        label: "Energy Base - Nuclear Power & Advanced Reactors",
        eliteOnly: false
      },
      {
        value: "energybaseoilproduction",
        label: "Energy Base - Oil & Gas Exploration & Production",
        eliteOnly: false
      },
      {
        value: "energybaseoilservices",
        label: "Energy Base - Oilfield Services & Equipment",
        eliteOnly: false
      },
      {
        value: "energybaseoilrefining",
        label: "Energy Base - Refining & Midstream Infrastructure",
        eliteOnly: false
      },
      {
        value: "energybaseutilities",
        label: "Energy Base - Utilities & Conventional Power Operators",
        eliteOnly: false
      },
      {
        value: "energycleanbatteries",
        label: "Energy Clean - Batteries & Storage",
        eliteOnly: false
      },
      {
        value: "energycleanbiofuels",
        label: "Energy Clean - Fuels & Bioenergy",
        eliteOnly: false
      },
      {
        value: "energycleangeothermal",
        label: "Energy Clean - Geothermal",
        eliteOnly: false
      },
      {
        value: "energycleanhydrogen",
        label: "Energy Clean - Hydrogen & Fuel Cells",
        eliteOnly: false
      },
      {
        value: "energycleanmaterials",
        label: "Energy Clean - Materials & Critical Metals",
        eliteOnly: false
      },
      {
        value: "energycleansmartgrid",
        label: "Energy Clean - Smart Grid & Electrification",
        eliteOnly: false
      },
      {
        value: "energycleansolar",
        label: "Energy Clean - Solar",
        eliteOnly: false
      },
      {
        value: "energycleanutilities",
        label: "Energy Clean - Utilities & Clean Power Operators",
        eliteOnly: false
      },
      {
        value: "energycleanwind",
        label: "Energy Clean - Wind",
        eliteOnly: false
      },
      {
        value: "entertainmentgaming",
        label: "Entertainment - Game Publishers & Developers",
        eliteOnly: false
      },
      {
        value: "entertainmentmusic",
        label: "Entertainment - Music & Audio Streaming",
        eliteOnly: false
      },
      {
        value: "entertainmentbetting",
        label: "Entertainment - Sports Betting, Wagering & Prediction Markets",
        eliteOnly: false
      },
      {
        value: "entertainmentinfrastructure",
        label: "Entertainment - Streaming & Gaming Infrastructure",
        eliteOnly: false
      },
      {
        value: "entertainmentvideo",
        label: "Entertainment - Video Streaming",
        eliteOnly: false
      },
      {
        value: "entertainmentgambling",
        label: "Entertainment - iGaming & Online Gambling",
        eliteOnly: false
      },
      {
        value: "environmentalairquality",
        label: "Environmental - Clean Technologies & Pollution Control",
        eliteOnly: false
      },
      {
        value: "environmentalclimate",
        label: "Environmental - Climate Technologies & Carbon Solutions",
        eliteOnly: false
      },
      {
        value: "environmentalagriculture",
        label: "Environmental - Sustainable Agriculture & Resource Management",
        eliteOnly: false
      },
      {
        value: "environmentalwaste",
        label: "Environmental - Waste Management & Recycling",
        eliteOnly: false
      },
      {
        value: "environmentalwater",
        label: "Environmental - Water Infrastructure & Treatment",
        eliteOnly: false
      },
      {
        value: "fintechblockchain",
        label: "FinTech - Crypto, Blockchain & Tokenization",
        eliteOnly: false
      },
      {
        value: "fintechneobanks",
        label: "FinTech - Digital Banking & Neobanks",
        eliteOnly: false
      },
      {
        value: "fintechpayments",
        label: "FinTech - Digital Payments & Merchant Infrastructure",
        eliteOnly: false
      },
      {
        value: "fintechexchanges",
        label: "FinTech - Exchanges & Market Infrastructure",
        eliteOnly: false
      },
      {
        value: "fintechinsurance",
        label: "FinTech - InsurTech & Embedded Insurance",
        eliteOnly: false
      },
      {
        value: "fintechlending",
        label: "FinTech - Lending, Credit & BNPL",
        eliteOnly: false
      },
      {
        value: "fintechtrading",
        label: "FinTech - Trading Platforms & WealthTech",
        eliteOnly: false
      },
      {
        value: "hardwaretelecom",
        label: "Hardware - Communications & Telecom",
        eliteOnly: false
      },
      {
        value: "hardwareelectronics",
        label: "Hardware - Consumer Electronics, Gaming PCs & Consoles",
        eliteOnly: false
      },
      {
        value: "hardwaredatacenters",
        label: "Hardware - Data Center Infrastructure",
        eliteOnly: false
      },
      {
        value: "hardwaregaming",
        label: "Hardware - Gaming & Immersive Pheriperals",
        eliteOnly: false
      },
      {
        value: "hardwareindustrialiot",
        label: "Hardware - Industrial & IoT",
        eliteOnly: false
      },
      {
        value: "hardwarenetworking",
        label: "Hardware - Networking Equipment",
        eliteOnly: false
      },
      {
        value: "hardwarenextgen",
        label: "Hardware - Next-Gen & Specialty",
        eliteOnly: false
      },
      {
        value: "hardwarepcsdevices",
        label: "Hardware - Personal Computing & Devices",
        eliteOnly: false
      },
      {
        value: "hardwareprinting",
        label: "Hardware - Printing & Imaging",
        eliteOnly: false
      },
      {
        value: "hardwareservers",
        label: "Hardware - Servers, OEMs & Enterprise Systems",
        eliteOnly: false
      },
      {
        value: "hardwarestorage",
        label: "Hardware - Storage",
        eliteOnly: false
      },
      {
        value: "healthcarediagnostics",
        label: "Healthcare - Diagnostics, Biomarkers & Liquid Biopsy",
        eliteOnly: false
      },
      {
        value: "healthcaretelemedicine",
        label: "Healthcare - Digital Health, Telemedicine & Remote Care",
        eliteOnly: false
      },
      {
        value: "healthcaregenomics",
        label: "Healthcare - Genomics & Personalized Medicine",
        eliteOnly: false
      },
      {
        value: "healthcareitdata",
        label: "Healthcare - IT, Services & Data Infrastructure",
        eliteOnly: false
      },
      {
        value: "healthcaredevices",
        label: "Healthcare - Medical Devices & HealthTech Hardware",
        eliteOnly: false
      },
      {
        value: "healthcaremetabolic",
        label: "Healthcare - Metabolic & Cardiometabolic",
        eliteOnly: false
      },
      {
        value: "healthcarenextgen",
        label: "Healthcare - Next-Gen Biotech Platforms",
        eliteOnly: false
      },
      {
        value: "healthcareoncology",
        label: "Healthcare - Oncology & Precision Cancer Therapeutics",
        eliteOnly: false
      },
      {
        value: "healthcaretherapeutics",
        label: "Healthcare - Regenerative Medicine, Psychedelics, Cannabis",
        eliteOnly: false
      },
      {
        value: "iotedgedevices",
        label: "IoT - Connected Devices & Sensors",
        eliteOnly: false
      },
      {
        value: "iotnetworking",
        label: "IoT - Connectivity & Networks",
        eliteOnly: false
      },
      {
        value: "iothardware",
        label: "IoT - Edge Computing & Hardware Infrastructure",
        eliteOnly: false
      },
      {
        value: "iotenterprise",
        label: "IoT - Industrial & Enterprise IoT",
        eliteOnly: false
      },
      {
        value: "iotsoftware",
        label: "IoT - Platforms, Software & Analytics",
        eliteOnly: false
      },
      {
        value: "iotsecurity",
        label: "IoT - Security & Data Management",
        eliteOnly: false
      },
      {
        value: "longevityagingpharma",
        label: "Longevity - Age-Related Pharmaceuticals & Biotech",
        eliteOnly: false
      },
      {
        value: "longevityhealthcare",
        label: "Longevity - Healthcare & Medical Devices",
        eliteOnly: false
      },
      {
        value: "longevityhealthyaging",
        label: "Longevity - Healthy Aging & Nutrition",
        eliteOnly: false
      },
      {
        value: "longevityseniorliving",
        label: "Longevity - Senior Living & Assisted Care",
        eliteOnly: false
      },
      {
        value: "nanotechproducts",
        label: "NanoTech - Consumer & Industrial Products",
        eliteOnly: false
      },
      {
        value: "nanotechenergy",
        label: "NanoTech - Energy & Environment",
        eliteOnly: false
      },
      {
        value: "nanotechelectronics",
        label: "NanoTech - Nanoelectronics & Semiconductors",
        eliteOnly: false
      },
      {
        value: "nanotechmaterials",
        label: "NanoTech - Nanomaterials & Manufacturing",
        eliteOnly: false
      },
      {
        value: "nanotechmedicine",
        label: "NanoTech - Nanomedicine & Drug Delivery",
        eliteOnly: false
      },
      {
        value: "nanotechresearchtools",
        label: "NanoTech - Research Tools & Advanced Instruments",
        eliteOnly: false
      },
      {
        value: "nutritionmealdelivery",
        label: "Nutrition - Food Delivery & Meal Kits",
        eliteOnly: false
      },
      {
        value: "nutritionsupplements",
        label: "Nutrition - Functional & Nutritional Supplements",
        eliteOnly: false
      },
      {
        value: "nutritionretailers",
        label: "Nutrition - Organic & Natural Food Retailers",
        eliteOnly: false
      },
      {
        value: "nutritionaltprotein",
        label: "Nutrition - Plant-Based Foods & Meat Alternatives",
        eliteOnly: false
      },
      {
        value: "quantumapplications",
        label: "Quantum  - Applications",
        eliteOnly: false
      },
      {
        value: "quantumcloud",
        label: "Quantum  - Cloud Ecosystems",
        eliteOnly: false
      },
      {
        value: "quantumenablingtech",
        label: "Quantum  - Enabling Technologies",
        eliteOnly: false
      },
      {
        value: "quantumhardware",
        label: "Quantum  - Hardware Platforms",
        eliteOnly: false
      },
      {
        value: "quantumnetworking",
        label: "Quantum  - Networking & Security",
        eliteOnly: false
      },
      {
        value: "quantumsoftware",
        label: "Quantum  - Software & Tools",
        eliteOnly: false
      },
      {
        value: "realestateittelecom",
        label: "Real Estate - Digital Infrastructure",
        eliteOnly: false
      },
      {
        value: "realestatewarehousing",
        label: "Real Estate - E-Commerce, Warehousing & Logistics",
        eliteOnly: false
      },
      {
        value: "realestatehealthcare",
        label: "Real Estate - Healthcare & Senior Living",
        eliteOnly: false
      },
      {
        value: "realestatehousing",
        label: "Real Estate - Housing, Urban Living & Demographics",
        eliteOnly: false
      },
      {
        value: "realestateoffice",
        label: "Real Estate - Office & Commercial Workspaces",
        eliteOnly: false
      },
      {
        value: "realestateretail",
        label: "Real Estate - Retail & Consumer Real Estate",
        eliteOnly: false
      },
      {
        value: "realestatetourism",
        label: "Real Estate - Travel, Leisure & Entertainment Properties",
        eliteOnly: false
      },
      {
        value: "roboticsavmobility",
        label: "Robotics - Autonomous Vehicles & Mobility",
        eliteOnly: false
      },
      {
        value: "roboticsautomation",
        label: "Robotics - Industrial Automation",
        eliteOnly: false
      },
      {
        value: "roboticslogistics",
        label: "Robotics - Logistics & Warehouse Robotics",
        eliteOnly: false
      },
      {
        value: "roboticsmedical",
        label: "Robotics - Medical & Surgical Robotics",
        eliteOnly: false
      },
      {
        value: "roboticsmachinevision",
        label: "Robotics - Sensors & Vision Systems",
        eliteOnly: false
      },
      {
        value: "roboticsconsumer",
        label: "Robotics - Service & Consumer Robotics",
        eliteOnly: false
      },
      {
        value: "semisanalog",
        label: "Semis - Analog, Mixed-Signal & Power Management",
        eliteOnly: false
      },
      {
        value: "semisdesigntools",
        label: "Semis - EDA Tools & Design Software",
        eliteOnly: false
      },
      {
        value: "semisnextgen",
        label: "Semis - Emerging Technologies",
        eliteOnly: false
      },
      {
        value: "semislithography",
        label: "Semis - Equipment, Lithography & Deposition",
        eliteOnly: false
      },
      {
        value: "semisfoundries",
        label: "Semis - Foundries & Manufacturing",
        eliteOnly: false
      },
      {
        value: "semiscompute",
        label: "Semis - Logic & CPUs, GPUs, Accelerators",
        eliteOnly: false
      },
      {
        value: "semismemory",
        label: "Semis - Memory & Storage",
        eliteOnly: false
      },
      {
        value: "semispackaging",
        label: "Semis - Testing, Packaging & Assembly",
        eliteOnly: false
      },
      {
        value: "semiswireless",
        label: "Semis - Wireless & Connectivity",
        eliteOnly: false
      },
      {
        value: "smarthomeautomation",
        label: "Smart Home - Automation & Control Systems",
        eliteOnly: false
      },
      {
        value: "smarthomedevices",
        label: "Smart Home - Connected Devices & Appliances",
        eliteOnly: false
      },
      {
        value: "smarthomenetworking",
        label: "Smart Home - Connectivity & Networking",
        eliteOnly: false
      },
      {
        value: "smarthomeenergy",
        label: "Smart Home - Energy & Utilities",
        eliteOnly: false
      },
      {
        value: "smarthomesecurity",
        label: "Smart Home - Security & Monitoring",
        eliteOnly: false
      },
      {
        value: "smarthomevoiceai",
        label: "Smart Home - Voice Assistants & AI Integration",
        eliteOnly: false
      },
      {
        value: "socialadvertising",
        label: "Social - Advertising Platforms",
        eliteOnly: false
      },
      {
        value: "socialgaming",
        label: "Social - Gaming Platforms",
        eliteOnly: false
      },
      {
        value: "socialvisualcontent",
        label: "Social - Image & Video Content Platforms",
        eliteOnly: false
      },
      {
        value: "socialnetworks",
        label: "Social - Networks & Communication Platforms",
        eliteOnly: false
      },
      {
        value: "socialniche",
        label: "Social - Niche Platforms",
        eliteOnly: false
      },
      {
        value: "softwarecollaboration",
        label: "Software - Collaboration & Communications",
        eliteOnly: false
      },
      {
        value: "softwarecrm",
        label: "Software - Customer Relationship Management & Marketing",
        eliteOnly: false
      },
      {
        value: "softwaresecurity",
        label: "Software - Cybersecurity",
        eliteOnly: false
      },
      {
        value: "softwaredataanalytics",
        label: "Software - Data & Analytics",
        eliteOnly: false
      },
      {
        value: "softwaredesign",
        label: "Software - Design, Creativity & Engineering",
        eliteOnly: false
      },
      {
        value: "softwaredevops",
        label: "Software - DevOps, Management & Observability",
        eliteOnly: false
      },
      {
        value: "softwareecommerce",
        label: "Software - E-Commerce & Digital Platforms",
        eliteOnly: false
      },
      {
        value: "softwareenterprise",
        label: "Software - Enterprise Resource Planning & Management",
        eliteOnly: false
      },
      {
        value: "softwaregaming",
        label: "Software - Gaming & Platforms",
        eliteOnly: false
      },
      {
        value: "softwarehsaas",
        label: "Software - Horizontal SaaS Platforms",
        eliteOnly: false
      },
      {
        value: "softwareos",
        label: "Software - Operating Systems",
        eliteOnly: false
      },
      {
        value: "softwarevsaas",
        label: "Software - Vertical SaaS Platforms",
        eliteOnly: false
      },
      {
        value: "spacedataanalytics",
        label: "Space - Data Analytics & Earth Observation",
        eliteOnly: false
      },
      {
        value: "spacedefense",
        label: "Space - Defense & Cybersecurity",
        eliteOnly: false
      },
      {
        value: "spaceinfrastructure",
        label: "Space - Infrastructure & Exploration",
        eliteOnly: false
      },
      {
        value: "spacelaunch",
        label: "Space - Logistics & Launch Services",
        eliteOnly: false
      },
      {
        value: "spacesatellites",
        label: "Space - Satellite Networks & Connectivity",
        eliteOnly: false
      },
      {
        value: "telecomg",
        label: "Telecom - 5G Technology & Semiconductors",
        eliteOnly: false
      },
      {
        value: "telecomcloudedge",
        label: "Telecom - Cloud & Edge Connectivity",
        eliteOnly: false
      },
      {
        value: "telecomenterprise",
        label: "Telecom - Enterprise & Unified Communications",
        eliteOnly: false
      },
      {
        value: "telecominfrastructure",
        label: "Telecom - Infrastructure & Equipment",
        eliteOnly: false
      },
      {
        value: "telecomsatcom",
        label: "Telecom - Satellite & Space Communication",
        eliteOnly: false
      },
      {
        value: "telecomwireless",
        label: "Telecom - Wireless Networks & Carriers",
        eliteOnly: false
      },
      {
        value: "transportationaircargo",
        label: "Transportation - Air Freight & Express Delivery",
        eliteOnly: false
      },
      {
        value: "transportationairtravel",
        label: "Transportation - Air Travel & Passenger Transportation",
        eliteOnly: false
      },
      {
        value: "transportationrail",
        label: "Transportation - Freight Rail & Infrastructure",
        eliteOnly: false
      },
      {
        value: "transportationinfrastructure",
        label: "Transportation - Infrastructure & Equipment",
        eliteOnly: false
      },
      {
        value: "transportationwarehousing",
        label: "Transportation - Logistics, Warehousing & Supply Chain Solutions",
        eliteOnly: false
      },
      {
        value: "transportationmaritime",
        label: "Transportation - Marine Shipping & Ports",
        eliteOnly: false
      },
      {
        value: "transportationtrucking",
        label: "Transportation - Trucking, LTL & Ground Freight",
        eliteOnly: false
      },
      {
        value: "transportationnextgen",
        label: "Transportation - Urban Mobility & Emerging Transport Tech",
        eliteOnly: false
      },
      {
        value: "varealityapplications",
        label: "V/A Reality - Content & Applications",
        eliteOnly: false
      },
      {
        value: "varealityenterprise",
        label: "V/A Reality - Enterprise & Industrial Solutions",
        eliteOnly: false
      },
      {
        value: "varealityhardware",
        label: "V/A Reality - Headsets & Hardware",
        eliteOnly: false
      },
      {
        value: "varealityinfrastructure",
        label: "V/A Reality - Infrastructure & Cloud Rendering",
        eliteOnly: false
      },
      {
        value: "varealitysoftware",
        label: "V/A Reality - Software Platforms & Operating Systems",
        eliteOnly: false
      },
      {
        value: "wearablesimmersive",
        label: "Wearables - Audio-Visual Immersive Devices",
        eliteOnly: false
      },
      {
        value: "wearablesmedical",
        label: "Wearables - Health Monitoring & Medical Devices",
        eliteOnly: false
      },
      {
        value: "wearablessmartwatches",
        label: "Wearables - Smartwatches & Fitness Devices",
        eliteOnly: false
      },
      {
        value: "wearablessoftware",
        label: "Wearables - Software & Ecosystems",
        eliteOnly: false
      },
      {
        value: "wearablessport",
        label: "Wearables - Sports, Fitness & Lifestyle Applications",
        eliteOnly: false
      },
      {
        value: "custom_subscription",
        label: "Custom (Elite only)",
        eliteOnly: true
      }
    ]
  },
  ta_alltime: {
    key: "ta_alltime",
    label: "All-Time High/Low",
    dataFilter: "ta_alltime",
    groups: [
      "technical",
      "all"
    ],
    options: [
      {
        value: "",
        label: "Any",
        eliteOnly: false
      },
      {
        value: "a0to10h",
        label: "0-10% above Low",
        eliteOnly: false
      },
      {
        value: "b0to10h",
        label: "0-10% below High",
        eliteOnly: false
      },
      {
        value: "a0to3h",
        label: "0-3% above Low",
        eliteOnly: false
      },
      {
        value: "b0to3h",
        label: "0-3% below High",
        eliteOnly: false
      },
      {
        value: "a0to5h",
        label: "0-5% above Low",
        eliteOnly: false
      },
      {
        value: "b0to5h",
        label: "0-5% below High",
        eliteOnly: false
      },
      {
        value: "a10h",
        label: "10% or more above Low",
        eliteOnly: false
      },
      {
        value: "b10h",
        label: "10% or more below High",
        eliteOnly: false
      },
      {
        value: "a100h",
        label: "100% or more above Low",
        eliteOnly: false
      },
      {
        value: "a120h",
        label: "120% or more above Low",
        eliteOnly: false
      },
      {
        value: "a15h",
        label: "15% or more above Low",
        eliteOnly: false
      },
      {
        value: "b15h",
        label: "15% or more below High",
        eliteOnly: false
      },
      {
        value: "a150h",
        label: "150% or more above Low",
        eliteOnly: false
      },
      {
        value: "a20h",
        label: "20% or more above Low",
        eliteOnly: false
      },
      {
        value: "b20h",
        label: "20% or more below High",
        eliteOnly: false
      },
      {
        value: "a200h",
        label: "200% or more above Low",
        eliteOnly: false
      },
      {
        value: "a30h",
        label: "30% or more above Low",
        eliteOnly: false
      },
      {
        value: "b30h",
        label: "30% or more below High",
        eliteOnly: false
      },
      {
        value: "a300h",
        label: "300% or more above Low",
        eliteOnly: false
      },
      {
        value: "a40h",
        label: "40% or more above Low",
        eliteOnly: false
      },
      {
        value: "b40h",
        label: "40% or more below High",
        eliteOnly: false
      },
      {
        value: "a5h",
        label: "5% or more above Low",
        eliteOnly: false
      },
      {
        value: "b5h",
        label: "5% or more below High",
        eliteOnly: false
      },
      {
        value: "a50h",
        label: "50% or more above Low",
        eliteOnly: false
      },
      {
        value: "b50h",
        label: "50% or more below High",
        eliteOnly: false
      },
      {
        value: "a500h",
        label: "500% or more above Low",
        eliteOnly: false
      },
      {
        value: "a60h",
        label: "60% or more above Low",
        eliteOnly: false
      },
      {
        value: "b60h",
        label: "60% or more below High",
        eliteOnly: false
      },
      {
        value: "a70h",
        label: "70% or more above Low",
        eliteOnly: false
      },
      {
        value: "b70h",
        label: "70% or more below High",
        eliteOnly: false
      },
      {
        value: "a80h",
        label: "80% or more above Low",
        eliteOnly: false
      },
      {
        value: "b80h",
        label: "80% or more below High",
        eliteOnly: false
      },
      {
        value: "a90h",
        label: "90% or more above Low",
        eliteOnly: false
      },
      {
        value: "b90h",
        label: "90% or more below High",
        eliteOnly: false
      },
      {
        value: "nh",
        label: "New High",
        eliteOnly: false
      },
      {
        value: "nl",
        label: "New Low",
        eliteOnly: false
      },
      {
        value: "custom_subscription",
        label: "Custom (Elite only)",
        eliteOnly: true
      }
    ]
  },
  ta_averagetruerange: {
    key: "ta_averagetruerange",
    label: "Average True Range",
    dataFilter: "ta_averagetruerange",
    groups: [
      "technical",
      "all"
    ],
    options: [
      {
        value: "",
        label: "Any",
        eliteOnly: false
      },
      {
        value: "o0.25",
        label: "Over 0.25",
        eliteOnly: false
      },
      {
        value: "o0.5",
        label: "Over 0.5",
        eliteOnly: false
      },
      {
        value: "o0.75",
        label: "Over 0.75",
        eliteOnly: false
      },
      {
        value: "o1",
        label: "Over 1",
        eliteOnly: false
      },
      {
        value: "o1.5",
        label: "Over 1.5",
        eliteOnly: false
      },
      {
        value: "o2",
        label: "Over 2",
        eliteOnly: false
      },
      {
        value: "o2.5",
        label: "Over 2.5",
        eliteOnly: false
      },
      {
        value: "o3",
        label: "Over 3",
        eliteOnly: false
      },
      {
        value: "o3.5",
        label: "Over 3.5",
        eliteOnly: false
      },
      {
        value: "o4",
        label: "Over 4",
        eliteOnly: false
      },
      {
        value: "o4.5",
        label: "Over 4.5",
        eliteOnly: false
      },
      {
        value: "o5",
        label: "Over 5",
        eliteOnly: false
      },
      {
        value: "u0.25",
        label: "Under 0.25",
        eliteOnly: false
      },
      {
        value: "u0.5",
        label: "Under 0.5",
        eliteOnly: false
      },
      {
        value: "u0.75",
        label: "Under 0.75",
        eliteOnly: false
      },
      {
        value: "u1",
        label: "Under 1",
        eliteOnly: false
      },
      {
        value: "u1.5",
        label: "Under 1.5",
        eliteOnly: false
      },
      {
        value: "u2",
        label: "Under 2",
        eliteOnly: false
      },
      {
        value: "u2.5",
        label: "Under 2.5",
        eliteOnly: false
      },
      {
        value: "u3",
        label: "Under 3",
        eliteOnly: false
      },
      {
        value: "u3.5",
        label: "Under 3.5",
        eliteOnly: false
      },
      {
        value: "u4",
        label: "Under 4",
        eliteOnly: false
      },
      {
        value: "u4.5",
        label: "Under 4.5",
        eliteOnly: false
      },
      {
        value: "u5",
        label: "Under 5",
        eliteOnly: false
      },
      {
        value: "custom_subscription",
        label: "Custom (Elite only)",
        eliteOnly: true
      }
    ]
  },
  ta_beta: {
    key: "ta_beta",
    label: "Beta",
    dataFilter: "ta_beta",
    groups: [
      "technical",
      "all"
    ],
    options: [
      {
        value: "",
        label: "Any",
        eliteOnly: false
      },
      {
        value: "0to0.5",
        label: "0 to 0.5",
        eliteOnly: false
      },
      {
        value: "0to1",
        label: "0 to 1",
        eliteOnly: false
      },
      {
        value: "0.5to1",
        label: "0.5 to 1",
        eliteOnly: false
      },
      {
        value: "0.5to1.5",
        label: "0.5 to 1.5",
        eliteOnly: false
      },
      {
        value: "1to1.5",
        label: "1 to 1.5",
        eliteOnly: false
      },
      {
        value: "1to2",
        label: "1 to 2",
        eliteOnly: false
      },
      {
        value: "o0",
        label: "Over 0",
        eliteOnly: false
      },
      {
        value: "o0.5",
        label: "Over 0.5",
        eliteOnly: false
      },
      {
        value: "o1",
        label: "Over 1",
        eliteOnly: false
      },
      {
        value: "o1.5",
        label: "Over 1.5",
        eliteOnly: false
      },
      {
        value: "o2",
        label: "Over 2",
        eliteOnly: false
      },
      {
        value: "o2.5",
        label: "Over 2.5",
        eliteOnly: false
      },
      {
        value: "o3",
        label: "Over 3",
        eliteOnly: false
      },
      {
        value: "o4",
        label: "Over 4",
        eliteOnly: false
      },
      {
        value: "u0",
        label: "Under 0",
        eliteOnly: false
      },
      {
        value: "u0.5",
        label: "Under 0.5",
        eliteOnly: false
      },
      {
        value: "u1",
        label: "Under 1",
        eliteOnly: false
      },
      {
        value: "u1.5",
        label: "Under 1.5",
        eliteOnly: false
      },
      {
        value: "u2",
        label: "Under 2",
        eliteOnly: false
      },
      {
        value: "custom_subscription",
        label: "Custom (Elite only)",
        eliteOnly: true
      }
    ]
  },
  ta_candlestick: {
    key: "ta_candlestick",
    label: "Candlestick",
    dataFilter: "ta_candlestick",
    groups: [
      "technical",
      "all"
    ],
    options: [
      {
        value: "",
        label: "Any",
        eliteOnly: false
      },
      {
        value: "d",
        label: "Doji",
        eliteOnly: false
      },
      {
        value: "dd",
        label: "Dragonfly Doji",
        eliteOnly: false
      },
      {
        value: "gd",
        label: "Gravestone Doji",
        eliteOnly: false
      },
      {
        value: "h",
        label: "Hammer",
        eliteOnly: false
      },
      {
        value: "ih",
        label: "Inverted Hammer",
        eliteOnly: false
      },
      {
        value: "lls",
        label: "Long Lower Shadow",
        eliteOnly: false
      },
      {
        value: "lus",
        label: "Long Upper Shadow",
        eliteOnly: false
      },
      {
        value: "mb",
        label: "Marubozu Black",
        eliteOnly: false
      },
      {
        value: "mw",
        label: "Marubozu White",
        eliteOnly: false
      },
      {
        value: "stb",
        label: "Spinning Top Black",
        eliteOnly: false
      },
      {
        value: "stw",
        label: "Spinning Top White",
        eliteOnly: false
      },
      {
        value: "custom_subscription",
        label: "Custom (Elite only)",
        eliteOnly: true
      }
    ]
  },
  ta_change: {
    key: "ta_change",
    label: "Change",
    dataFilter: "ta_change",
    groups: [
      "technical",
      "all"
    ],
    options: [
      {
        value: "",
        label: "Any",
        eliteOnly: false
      },
      {
        value: "d",
        label: "Down",
        eliteOnly: false
      },
      {
        value: "d1",
        label: "Down 1%",
        eliteOnly: false
      },
      {
        value: "d10",
        label: "Down 10%",
        eliteOnly: false
      },
      {
        value: "d15",
        label: "Down 15%",
        eliteOnly: false
      },
      {
        value: "d2",
        label: "Down 2%",
        eliteOnly: false
      },
      {
        value: "d20",
        label: "Down 20%",
        eliteOnly: false
      },
      {
        value: "d3",
        label: "Down 3%",
        eliteOnly: false
      },
      {
        value: "d4",
        label: "Down 4%",
        eliteOnly: false
      },
      {
        value: "d5",
        label: "Down 5%",
        eliteOnly: false
      },
      {
        value: "d6",
        label: "Down 6%",
        eliteOnly: false
      },
      {
        value: "d7",
        label: "Down 7%",
        eliteOnly: false
      },
      {
        value: "d8",
        label: "Down 8%",
        eliteOnly: false
      },
      {
        value: "d9",
        label: "Down 9%",
        eliteOnly: false
      },
      {
        value: "u",
        label: "Up",
        eliteOnly: false
      },
      {
        value: "u1",
        label: "Up 1%",
        eliteOnly: false
      },
      {
        value: "u10",
        label: "Up 10%",
        eliteOnly: false
      },
      {
        value: "u15",
        label: "Up 15%",
        eliteOnly: false
      },
      {
        value: "u2",
        label: "Up 2%",
        eliteOnly: false
      },
      {
        value: "u20",
        label: "Up 20%",
        eliteOnly: false
      },
      {
        value: "u3",
        label: "Up 3%",
        eliteOnly: false
      },
      {
        value: "u4",
        label: "Up 4%",
        eliteOnly: false
      },
      {
        value: "u5",
        label: "Up 5%",
        eliteOnly: false
      },
      {
        value: "u6",
        label: "Up 6%",
        eliteOnly: false
      },
      {
        value: "u7",
        label: "Up 7%",
        eliteOnly: false
      },
      {
        value: "u8",
        label: "Up 8%",
        eliteOnly: false
      },
      {
        value: "u9",
        label: "Up 9%",
        eliteOnly: false
      },
      {
        value: "custom_subscription",
        label: "Custom (Elite only)",
        eliteOnly: true
      }
    ]
  },
  ta_changeopen: {
    key: "ta_changeopen",
    label: "Change from Open",
    dataFilter: "ta_changeopen",
    groups: [
      "technical",
      "all"
    ],
    options: [
      {
        value: "",
        label: "Any",
        eliteOnly: false
      },
      {
        value: "d",
        label: "Down",
        eliteOnly: false
      },
      {
        value: "d1",
        label: "Down 1%",
        eliteOnly: false
      },
      {
        value: "d10",
        label: "Down 10%",
        eliteOnly: false
      },
      {
        value: "d15",
        label: "Down 15%",
        eliteOnly: false
      },
      {
        value: "d2",
        label: "Down 2%",
        eliteOnly: false
      },
      {
        value: "d20",
        label: "Down 20%",
        eliteOnly: false
      },
      {
        value: "d3",
        label: "Down 3%",
        eliteOnly: false
      },
      {
        value: "d4",
        label: "Down 4%",
        eliteOnly: false
      },
      {
        value: "d5",
        label: "Down 5%",
        eliteOnly: false
      },
      {
        value: "d6",
        label: "Down 6%",
        eliteOnly: false
      },
      {
        value: "d7",
        label: "Down 7%",
        eliteOnly: false
      },
      {
        value: "d8",
        label: "Down 8%",
        eliteOnly: false
      },
      {
        value: "d9",
        label: "Down 9%",
        eliteOnly: false
      },
      {
        value: "u",
        label: "Up",
        eliteOnly: false
      },
      {
        value: "u1",
        label: "Up 1%",
        eliteOnly: false
      },
      {
        value: "u10",
        label: "Up 10%",
        eliteOnly: false
      },
      {
        value: "u15",
        label: "Up 15%",
        eliteOnly: false
      },
      {
        value: "u2",
        label: "Up 2%",
        eliteOnly: false
      },
      {
        value: "u20",
        label: "Up 20%",
        eliteOnly: false
      },
      {
        value: "u3",
        label: "Up 3%",
        eliteOnly: false
      },
      {
        value: "u4",
        label: "Up 4%",
        eliteOnly: false
      },
      {
        value: "u5",
        label: "Up 5%",
        eliteOnly: false
      },
      {
        value: "u6",
        label: "Up 6%",
        eliteOnly: false
      },
      {
        value: "u7",
        label: "Up 7%",
        eliteOnly: false
      },
      {
        value: "u8",
        label: "Up 8%",
        eliteOnly: false
      },
      {
        value: "u9",
        label: "Up 9%",
        eliteOnly: false
      },
      {
        value: "custom_subscription",
        label: "Custom (Elite only)",
        eliteOnly: true
      }
    ]
  },
  ta_gap: {
    key: "ta_gap",
    label: "Gap",
    dataFilter: "ta_gap",
    groups: [
      "technical",
      "all"
    ],
    options: [
      {
        value: "",
        label: "Any",
        eliteOnly: false
      },
      {
        value: "d",
        label: "Down",
        eliteOnly: false
      },
      {
        value: "d0",
        label: "Down 0%",
        eliteOnly: false
      },
      {
        value: "d1",
        label: "Down 1%",
        eliteOnly: false
      },
      {
        value: "d10",
        label: "Down 10%",
        eliteOnly: false
      },
      {
        value: "d15",
        label: "Down 15%",
        eliteOnly: false
      },
      {
        value: "d2",
        label: "Down 2%",
        eliteOnly: false
      },
      {
        value: "d20",
        label: "Down 20%",
        eliteOnly: false
      },
      {
        value: "d3",
        label: "Down 3%",
        eliteOnly: false
      },
      {
        value: "d4",
        label: "Down 4%",
        eliteOnly: false
      },
      {
        value: "d5",
        label: "Down 5%",
        eliteOnly: false
      },
      {
        value: "d6",
        label: "Down 6%",
        eliteOnly: false
      },
      {
        value: "d7",
        label: "Down 7%",
        eliteOnly: false
      },
      {
        value: "d8",
        label: "Down 8%",
        eliteOnly: false
      },
      {
        value: "d9",
        label: "Down 9%",
        eliteOnly: false
      },
      {
        value: "u",
        label: "Up",
        eliteOnly: false
      },
      {
        value: "u0",
        label: "Up 0%",
        eliteOnly: false
      },
      {
        value: "u1",
        label: "Up 1%",
        eliteOnly: false
      },
      {
        value: "u10",
        label: "Up 10%",
        eliteOnly: false
      },
      {
        value: "u15",
        label: "Up 15%",
        eliteOnly: false
      },
      {
        value: "u2",
        label: "Up 2%",
        eliteOnly: false
      },
      {
        value: "u20",
        label: "Up 20%",
        eliteOnly: false
      },
      {
        value: "u3",
        label: "Up 3%",
        eliteOnly: false
      },
      {
        value: "u4",
        label: "Up 4%",
        eliteOnly: false
      },
      {
        value: "u5",
        label: "Up 5%",
        eliteOnly: false
      },
      {
        value: "u6",
        label: "Up 6%",
        eliteOnly: false
      },
      {
        value: "u7",
        label: "Up 7%",
        eliteOnly: false
      },
      {
        value: "u8",
        label: "Up 8%",
        eliteOnly: false
      },
      {
        value: "u9",
        label: "Up 9%",
        eliteOnly: false
      },
      {
        value: "custom_subscription",
        label: "Custom (Elite only)",
        eliteOnly: true
      }
    ]
  },
  ta_highlow20d: {
    key: "ta_highlow20d",
    label: "20-Day High/Low",
    dataFilter: "ta_highlow20d",
    groups: [
      "technical",
      "all"
    ],
    options: [
      {
        value: "",
        label: "Any",
        eliteOnly: false
      },
      {
        value: "a0to10h",
        label: "0-10% above Low",
        eliteOnly: false
      },
      {
        value: "b0to10h",
        label: "0-10% below High",
        eliteOnly: false
      },
      {
        value: "a0to3h",
        label: "0-3% above Low",
        eliteOnly: false
      },
      {
        value: "b0to3h",
        label: "0-3% below High",
        eliteOnly: false
      },
      {
        value: "a0to5h",
        label: "0-5% above Low",
        eliteOnly: false
      },
      {
        value: "b0to5h",
        label: "0-5% below High",
        eliteOnly: false
      },
      {
        value: "a10h",
        label: "10% or more above Low",
        eliteOnly: false
      },
      {
        value: "b10h",
        label: "10% or more below High",
        eliteOnly: false
      },
      {
        value: "a15h",
        label: "15% or more above Low",
        eliteOnly: false
      },
      {
        value: "b15h",
        label: "15% or more below High",
        eliteOnly: false
      },
      {
        value: "a20h",
        label: "20% or more above Low",
        eliteOnly: false
      },
      {
        value: "b20h",
        label: "20% or more below High",
        eliteOnly: false
      },
      {
        value: "a30h",
        label: "30% or more above Low",
        eliteOnly: false
      },
      {
        value: "b30h",
        label: "30% or more below High",
        eliteOnly: false
      },
      {
        value: "a40h",
        label: "40% or more above Low",
        eliteOnly: false
      },
      {
        value: "b40h",
        label: "40% or more below High",
        eliteOnly: false
      },
      {
        value: "a5h",
        label: "5% or more above Low",
        eliteOnly: false
      },
      {
        value: "b5h",
        label: "5% or more below High",
        eliteOnly: false
      },
      {
        value: "a50h",
        label: "50% or more above Low",
        eliteOnly: false
      },
      {
        value: "b50h",
        label: "50% or more below High",
        eliteOnly: false
      },
      {
        value: "nh",
        label: "New High",
        eliteOnly: false
      },
      {
        value: "nl",
        label: "New Low",
        eliteOnly: false
      },
      {
        value: "custom_subscription",
        label: "Custom (Elite only)",
        eliteOnly: true
      }
    ]
  },
  ta_highlow50d: {
    key: "ta_highlow50d",
    label: "50-Day High/Low",
    dataFilter: "ta_highlow50d",
    groups: [
      "technical",
      "all"
    ],
    options: [
      {
        value: "",
        label: "Any",
        eliteOnly: false
      },
      {
        value: "a0to10h",
        label: "0-10% above Low",
        eliteOnly: false
      },
      {
        value: "b0to10h",
        label: "0-10% below High",
        eliteOnly: false
      },
      {
        value: "a0to3h",
        label: "0-3% above Low",
        eliteOnly: false
      },
      {
        value: "b0to3h",
        label: "0-3% below High",
        eliteOnly: false
      },
      {
        value: "a0to5h",
        label: "0-5% above Low",
        eliteOnly: false
      },
      {
        value: "b0to5h",
        label: "0-5% below High",
        eliteOnly: false
      },
      {
        value: "a10h",
        label: "10% or more above Low",
        eliteOnly: false
      },
      {
        value: "b10h",
        label: "10% or more below High",
        eliteOnly: false
      },
      {
        value: "a15h",
        label: "15% or more above Low",
        eliteOnly: false
      },
      {
        value: "b15h",
        label: "15% or more below High",
        eliteOnly: false
      },
      {
        value: "a20h",
        label: "20% or more above Low",
        eliteOnly: false
      },
      {
        value: "b20h",
        label: "20% or more below High",
        eliteOnly: false
      },
      {
        value: "a30h",
        label: "30% or more above Low",
        eliteOnly: false
      },
      {
        value: "b30h",
        label: "30% or more below High",
        eliteOnly: false
      },
      {
        value: "a40h",
        label: "40% or more above Low",
        eliteOnly: false
      },
      {
        value: "b40h",
        label: "40% or more below High",
        eliteOnly: false
      },
      {
        value: "a5h",
        label: "5% or more above Low",
        eliteOnly: false
      },
      {
        value: "b5h",
        label: "5% or more below High",
        eliteOnly: false
      },
      {
        value: "a50h",
        label: "50% or more above Low",
        eliteOnly: false
      },
      {
        value: "b50h",
        label: "50% or more below High",
        eliteOnly: false
      },
      {
        value: "nh",
        label: "New High",
        eliteOnly: false
      },
      {
        value: "nl",
        label: "New Low",
        eliteOnly: false
      },
      {
        value: "custom_subscription",
        label: "Custom (Elite only)",
        eliteOnly: true
      }
    ]
  },
  ta_highlow52w: {
    key: "ta_highlow52w",
    label: "52-Week High/Low",
    dataFilter: "ta_highlow52w",
    groups: [
      "technical",
      "all"
    ],
    options: [
      {
        value: "",
        label: "Any",
        eliteOnly: false
      },
      {
        value: "a0to10h",
        label: "0-10% above Low",
        eliteOnly: false
      },
      {
        value: "b0to10h",
        label: "0-10% below High",
        eliteOnly: false
      },
      {
        value: "a0to3h",
        label: "0-3% above Low",
        eliteOnly: false
      },
      {
        value: "b0to3h",
        label: "0-3% below High",
        eliteOnly: false
      },
      {
        value: "a0to5h",
        label: "0-5% above Low",
        eliteOnly: false
      },
      {
        value: "b0to5h",
        label: "0-5% below High",
        eliteOnly: false
      },
      {
        value: "a10h",
        label: "10% or more above Low",
        eliteOnly: false
      },
      {
        value: "b10h",
        label: "10% or more below High",
        eliteOnly: false
      },
      {
        value: "a100h",
        label: "100% or more above Low",
        eliteOnly: false
      },
      {
        value: "a120h",
        label: "120% or more above Low",
        eliteOnly: false
      },
      {
        value: "a15h",
        label: "15% or more above Low",
        eliteOnly: false
      },
      {
        value: "b15h",
        label: "15% or more below High",
        eliteOnly: false
      },
      {
        value: "a150h",
        label: "150% or more above Low",
        eliteOnly: false
      },
      {
        value: "a20h",
        label: "20% or more above Low",
        eliteOnly: false
      },
      {
        value: "b20h",
        label: "20% or more below High",
        eliteOnly: false
      },
      {
        value: "a200h",
        label: "200% or more above Low",
        eliteOnly: false
      },
      {
        value: "a30h",
        label: "30% or more above Low",
        eliteOnly: false
      },
      {
        value: "b30h",
        label: "30% or more below High",
        eliteOnly: false
      },
      {
        value: "a300h",
        label: "300% or more above Low",
        eliteOnly: false
      },
      {
        value: "a40h",
        label: "40% or more above Low",
        eliteOnly: false
      },
      {
        value: "b40h",
        label: "40% or more below High",
        eliteOnly: false
      },
      {
        value: "a5h",
        label: "5% or more above Low",
        eliteOnly: false
      },
      {
        value: "b5h",
        label: "5% or more below High",
        eliteOnly: false
      },
      {
        value: "a50h",
        label: "50% or more above Low",
        eliteOnly: false
      },
      {
        value: "b50h",
        label: "50% or more below High",
        eliteOnly: false
      },
      {
        value: "a500h",
        label: "500% or more above Low",
        eliteOnly: false
      },
      {
        value: "a60h",
        label: "60% or more above Low",
        eliteOnly: false
      },
      {
        value: "b60h",
        label: "60% or more below High",
        eliteOnly: false
      },
      {
        value: "a70h",
        label: "70% or more above Low",
        eliteOnly: false
      },
      {
        value: "b70h",
        label: "70% or more below High",
        eliteOnly: false
      },
      {
        value: "a80h",
        label: "80% or more above Low",
        eliteOnly: false
      },
      {
        value: "b80h",
        label: "80% or more below High",
        eliteOnly: false
      },
      {
        value: "a90h",
        label: "90% or more above Low",
        eliteOnly: false
      },
      {
        value: "b90h",
        label: "90% or more below High",
        eliteOnly: false
      },
      {
        value: "nh",
        label: "New High",
        eliteOnly: false
      },
      {
        value: "nl",
        label: "New Low",
        eliteOnly: false
      },
      {
        value: "custom_subscription",
        label: "Custom (Elite only)",
        eliteOnly: true
      }
    ]
  },
  ta_pattern: {
    key: "ta_pattern",
    label: "Pattern",
    dataFilter: "ta_pattern",
    groups: [
      "technical",
      "all"
    ],
    options: [
      {
        value: "",
        label: "Any",
        eliteOnly: false
      },
      {
        value: "channel",
        label: "Channel",
        eliteOnly: false
      },
      {
        value: "channel2",
        label: "Channel (Strong)",
        eliteOnly: false
      },
      {
        value: "channeldown",
        label: "Channel Down",
        eliteOnly: false
      },
      {
        value: "channeldown2",
        label: "Channel Down (Strong)",
        eliteOnly: false
      },
      {
        value: "channelup",
        label: "Channel Up",
        eliteOnly: false
      },
      {
        value: "channelup2",
        label: "Channel Up (Strong)",
        eliteOnly: false
      },
      {
        value: "doublebottom",
        label: "Double Bottom",
        eliteOnly: false
      },
      {
        value: "doubletop",
        label: "Double Top",
        eliteOnly: false
      },
      {
        value: "headandshoulders",
        label: "Head & Shoulders",
        eliteOnly: false
      },
      {
        value: "headandshouldersinv",
        label: "Head & Shoulders Inverse",
        eliteOnly: false
      },
      {
        value: "horizontal",
        label: "Horizontal S/R",
        eliteOnly: false
      },
      {
        value: "horizontal2",
        label: "Horizontal S/R (Strong)",
        eliteOnly: false
      },
      {
        value: "multiplebottom",
        label: "Multiple Bottom",
        eliteOnly: false
      },
      {
        value: "multipletop",
        label: "Multiple Top",
        eliteOnly: false
      },
      {
        value: "tlresistance",
        label: "TL Resistance",
        eliteOnly: false
      },
      {
        value: "tlresistance2",
        label: "TL Resistance (Strong)",
        eliteOnly: false
      },
      {
        value: "tlsupport",
        label: "TL Support",
        eliteOnly: false
      },
      {
        value: "tlsupport2",
        label: "TL Support (Strong)",
        eliteOnly: false
      },
      {
        value: "wedgeresistance",
        label: "Triangle Ascending",
        eliteOnly: false
      },
      {
        value: "wedgeresistance2",
        label: "Triangle Ascending (Strong)",
        eliteOnly: false
      },
      {
        value: "wedgesupport",
        label: "Triangle Descending",
        eliteOnly: false
      },
      {
        value: "wedgesupport2",
        label: "Triangle Descending (Strong)",
        eliteOnly: false
      },
      {
        value: "wedge",
        label: "Wedge",
        eliteOnly: false
      },
      {
        value: "wedge2",
        label: "Wedge (Strong)",
        eliteOnly: false
      },
      {
        value: "wedgedown",
        label: "Wedge Down",
        eliteOnly: false
      },
      {
        value: "wedgedown2",
        label: "Wedge Down (Strong)",
        eliteOnly: false
      },
      {
        value: "wedgeup",
        label: "Wedge Up",
        eliteOnly: false
      },
      {
        value: "wedgeup2",
        label: "Wedge Up (Strong)",
        eliteOnly: false
      },
      {
        value: "custom_subscription",
        label: "Custom (Elite only)",
        eliteOnly: true
      }
    ]
  },
  ta_perf: {
    key: "ta_perf",
    label: "Performance",
    dataFilter: "ta_perf",
    groups: [
      "technical",
      "all"
    ],
    options: [
      {
        value: "",
        label: "Any",
        eliteOnly: false
      },
      {
        value: "10y10o",
        label: "10 Years +10%",
        eliteOnly: false
      },
      {
        value: "10y100o",
        label: "10 Years +100%",
        eliteOnly: false
      },
      {
        value: "10y1000o",
        label: "10 Years +1000%",
        eliteOnly: false
      },
      {
        value: "10y20o",
        label: "10 Years +20%",
        eliteOnly: false
      },
      {
        value: "10y200o",
        label: "10 Years +200%",
        eliteOnly: false
      },
      {
        value: "10y30o",
        label: "10 Years +30%",
        eliteOnly: false
      },
      {
        value: "10y300o",
        label: "10 Years +300%",
        eliteOnly: false
      },
      {
        value: "10y50o",
        label: "10 Years +50%",
        eliteOnly: false
      },
      {
        value: "10y500o",
        label: "10 Years +500%",
        eliteOnly: false
      },
      {
        value: "10y10u",
        label: "10 Years -10%",
        eliteOnly: false
      },
      {
        value: "10y20u",
        label: "10 Years -20%",
        eliteOnly: false
      },
      {
        value: "10y30u",
        label: "10 Years -30%",
        eliteOnly: false
      },
      {
        value: "10y50u",
        label: "10 Years -50%",
        eliteOnly: false
      },
      {
        value: "10y75u",
        label: "10 Years -75%",
        eliteOnly: false
      },
      {
        value: "10y90u",
        label: "10 Years -90%",
        eliteOnly: false
      },
      {
        value: "10ydown",
        label: "10 Years Down",
        eliteOnly: false
      },
      {
        value: "10yup",
        label: "10 Years Up",
        eliteOnly: false
      },
      {
        value: "3y10o",
        label: "3 Years +10%",
        eliteOnly: false
      },
      {
        value: "3y100o",
        label: "3 Years +100%",
        eliteOnly: false
      },
      {
        value: "3y1000o",
        label: "3 Years +1000%",
        eliteOnly: false
      },
      {
        value: "3y20o",
        label: "3 Years +20%",
        eliteOnly: false
      },
      {
        value: "3y200o",
        label: "3 Years +200%",
        eliteOnly: false
      },
      {
        value: "3y30o",
        label: "3 Years +30%",
        eliteOnly: false
      },
      {
        value: "3y300o",
        label: "3 Years +300%",
        eliteOnly: false
      },
      {
        value: "3y50o",
        label: "3 Years +50%",
        eliteOnly: false
      },
      {
        value: "3y500o",
        label: "3 Years +500%",
        eliteOnly: false
      },
      {
        value: "3y10u",
        label: "3 Years -10%",
        eliteOnly: false
      },
      {
        value: "3y20u",
        label: "3 Years -20%",
        eliteOnly: false
      },
      {
        value: "3y30u",
        label: "3 Years -30%",
        eliteOnly: false
      },
      {
        value: "3y50u",
        label: "3 Years -50%",
        eliteOnly: false
      },
      {
        value: "3y75u",
        label: "3 Years -75%",
        eliteOnly: false
      },
      {
        value: "3y90u",
        label: "3 Years -90%",
        eliteOnly: false
      },
      {
        value: "3ydown",
        label: "3 Years Down",
        eliteOnly: false
      },
      {
        value: "3yup",
        label: "3 Years Up",
        eliteOnly: false
      },
      {
        value: "5y10o",
        label: "5 Years +10%",
        eliteOnly: false
      },
      {
        value: "5y100o",
        label: "5 Years +100%",
        eliteOnly: false
      },
      {
        value: "5y1000o",
        label: "5 Years +1000%",
        eliteOnly: false
      },
      {
        value: "5y20o",
        label: "5 Years +20%",
        eliteOnly: false
      },
      {
        value: "5y200o",
        label: "5 Years +200%",
        eliteOnly: false
      },
      {
        value: "5y30o",
        label: "5 Years +30%",
        eliteOnly: false
      },
      {
        value: "5y300o",
        label: "5 Years +300%",
        eliteOnly: false
      },
      {
        value: "5y50o",
        label: "5 Years +50%",
        eliteOnly: false
      },
      {
        value: "5y500o",
        label: "5 Years +500%",
        eliteOnly: false
      },
      {
        value: "5y10u",
        label: "5 Years -10%",
        eliteOnly: false
      },
      {
        value: "5y20u",
        label: "5 Years -20%",
        eliteOnly: false
      },
      {
        value: "5y30u",
        label: "5 Years -30%",
        eliteOnly: false
      },
      {
        value: "5y50u",
        label: "5 Years -50%",
        eliteOnly: false
      },
      {
        value: "5y75u",
        label: "5 Years -75%",
        eliteOnly: false
      },
      {
        value: "5y90u",
        label: "5 Years -90%",
        eliteOnly: false
      },
      {
        value: "5ydown",
        label: "5 Years Down",
        eliteOnly: false
      },
      {
        value: "5yup",
        label: "5 Years Up",
        eliteOnly: false
      },
      {
        value: "26w10o",
        label: "Half +10%",
        eliteOnly: false
      },
      {
        value: "26w100o",
        label: "Half +100%",
        eliteOnly: false
      },
      {
        value: "26w20o",
        label: "Half +20%",
        eliteOnly: false
      },
      {
        value: "26w30o",
        label: "Half +30%",
        eliteOnly: false
      },
      {
        value: "26w50o",
        label: "Half +50%",
        eliteOnly: false
      },
      {
        value: "26w10u",
        label: "Half -10%",
        eliteOnly: false
      },
      {
        value: "26w20u",
        label: "Half -20%",
        eliteOnly: false
      },
      {
        value: "26w30u",
        label: "Half -30%",
        eliteOnly: false
      },
      {
        value: "26w50u",
        label: "Half -50%",
        eliteOnly: false
      },
      {
        value: "26w75u",
        label: "Half -75%",
        eliteOnly: false
      },
      {
        value: "26wdown",
        label: "Half Down",
        eliteOnly: false
      },
      {
        value: "26wup",
        label: "Half Up",
        eliteOnly: false
      },
      {
        value: "4w10o",
        label: "Month +10%",
        eliteOnly: false
      },
      {
        value: "4w20o",
        label: "Month +20%",
        eliteOnly: false
      },
      {
        value: "4w30o",
        label: "Month +30%",
        eliteOnly: false
      },
      {
        value: "4w50o",
        label: "Month +50%",
        eliteOnly: false
      },
      {
        value: "4w10u",
        label: "Month -10%",
        eliteOnly: false
      },
      {
        value: "4w20u",
        label: "Month -20%",
        eliteOnly: false
      },
      {
        value: "4w30u",
        label: "Month -30%",
        eliteOnly: false
      },
      {
        value: "4w50u",
        label: "Month -50%",
        eliteOnly: false
      },
      {
        value: "4wdown",
        label: "Month Down",
        eliteOnly: false
      },
      {
        value: "4wup",
        label: "Month Up",
        eliteOnly: false
      },
      {
        value: "13w10o",
        label: "Quarter +10%",
        eliteOnly: false
      },
      {
        value: "13w20o",
        label: "Quarter +20%",
        eliteOnly: false
      },
      {
        value: "13w30o",
        label: "Quarter +30%",
        eliteOnly: false
      },
      {
        value: "13w50o",
        label: "Quarter +50%",
        eliteOnly: false
      },
      {
        value: "13w10u",
        label: "Quarter -10%",
        eliteOnly: false
      },
      {
        value: "13w20u",
        label: "Quarter -20%",
        eliteOnly: false
      },
      {
        value: "13w30u",
        label: "Quarter -30%",
        eliteOnly: false
      },
      {
        value: "13w50u",
        label: "Quarter -50%",
        eliteOnly: false
      },
      {
        value: "13wdown",
        label: "Quarter Down",
        eliteOnly: false
      },
      {
        value: "13wup",
        label: "Quarter Up",
        eliteOnly: false
      },
      {
        value: "d10o",
        label: "Today +10%",
        eliteOnly: false
      },
      {
        value: "d15o",
        label: "Today +15%",
        eliteOnly: false
      },
      {
        value: "d5o",
        label: "Today +5%",
        eliteOnly: false
      },
      {
        value: "d10u",
        label: "Today -10%",
        eliteOnly: false
      },
      {
        value: "d15u",
        label: "Today -15%",
        eliteOnly: false
      },
      {
        value: "d5u",
        label: "Today -5%",
        eliteOnly: false
      },
      {
        value: "ddown",
        label: "Today Down",
        eliteOnly: false
      },
      {
        value: "dup",
        label: "Today Up",
        eliteOnly: false
      },
      {
        value: "1w10o",
        label: "Week +10%",
        eliteOnly: false
      },
      {
        value: "1w20o",
        label: "Week +20%",
        eliteOnly: false
      },
      {
        value: "1w30o",
        label: "Week +30%",
        eliteOnly: false
      },
      {
        value: "1w10u",
        label: "Week -10%",
        eliteOnly: false
      },
      {
        value: "1w20u",
        label: "Week -20%",
        eliteOnly: false
      },
      {
        value: "1w30u",
        label: "Week -30%",
        eliteOnly: false
      },
      {
        value: "1wdown",
        label: "Week Down",
        eliteOnly: false
      },
      {
        value: "1wup",
        label: "Week Up",
        eliteOnly: false
      },
      {
        value: "ytd10o",
        label: "YTD +10%",
        eliteOnly: false
      },
      {
        value: "ytd100o",
        label: "YTD +100%",
        eliteOnly: false
      },
      {
        value: "ytd20o",
        label: "YTD +20%",
        eliteOnly: false
      },
      {
        value: "ytd30o",
        label: "YTD +30%",
        eliteOnly: false
      },
      {
        value: "ytd5o",
        label: "YTD +5%",
        eliteOnly: false
      },
      {
        value: "ytd50o",
        label: "YTD +50%",
        eliteOnly: false
      },
      {
        value: "ytd10u",
        label: "YTD -10%",
        eliteOnly: false
      },
      {
        value: "ytd20u",
        label: "YTD -20%",
        eliteOnly: false
      },
      {
        value: "ytd30u",
        label: "YTD -30%",
        eliteOnly: false
      },
      {
        value: "ytd5u",
        label: "YTD -5%",
        eliteOnly: false
      },
      {
        value: "ytd50u",
        label: "YTD -50%",
        eliteOnly: false
      },
      {
        value: "ytd75u",
        label: "YTD -75%",
        eliteOnly: false
      },
      {
        value: "ytddown",
        label: "YTD Down",
        eliteOnly: false
      },
      {
        value: "ytdup",
        label: "YTD Up",
        eliteOnly: false
      },
      {
        value: "52w10o",
        label: "Year +10%",
        eliteOnly: false
      },
      {
        value: "52w100o",
        label: "Year +100%",
        eliteOnly: false
      },
      {
        value: "52w20o",
        label: "Year +20%",
        eliteOnly: false
      },
      {
        value: "52w200o",
        label: "Year +200%",
        eliteOnly: false
      },
      {
        value: "52w30o",
        label: "Year +30%",
        eliteOnly: false
      },
      {
        value: "52w300o",
        label: "Year +300%",
        eliteOnly: false
      },
      {
        value: "52w50o",
        label: "Year +50%",
        eliteOnly: false
      },
      {
        value: "52w500o",
        label: "Year +500%",
        eliteOnly: false
      },
      {
        value: "52w10u",
        label: "Year -10%",
        eliteOnly: false
      },
      {
        value: "52w20u",
        label: "Year -20%",
        eliteOnly: false
      },
      {
        value: "52w30u",
        label: "Year -30%",
        eliteOnly: false
      },
      {
        value: "52w50u",
        label: "Year -50%",
        eliteOnly: false
      },
      {
        value: "52w75u",
        label: "Year -75%",
        eliteOnly: false
      },
      {
        value: "52wdown",
        label: "Year Down",
        eliteOnly: false
      },
      {
        value: "52wup",
        label: "Year Up",
        eliteOnly: false
      },
      {
        value: "custom_subscription",
        label: "Intraday (Elite only)",
        eliteOnly: true
      }
    ]
  },
  ta_perf2: {
    key: "ta_perf2",
    label: "Performance 2",
    dataFilter: "ta_perf2",
    groups: [
      "technical",
      "all"
    ],
    options: [
      {
        value: "",
        label: "Any",
        eliteOnly: false
      },
      {
        value: "10y10o",
        label: "10 Year +10%",
        eliteOnly: false
      },
      {
        value: "10y100o",
        label: "10 Year +100%",
        eliteOnly: false
      },
      {
        value: "10y1000o",
        label: "10 Year +1000%",
        eliteOnly: false
      },
      {
        value: "10y20o",
        label: "10 Year +20%",
        eliteOnly: false
      },
      {
        value: "10y200o",
        label: "10 Year +200%",
        eliteOnly: false
      },
      {
        value: "10y30o",
        label: "10 Year +30%",
        eliteOnly: false
      },
      {
        value: "10y300o",
        label: "10 Year +300%",
        eliteOnly: false
      },
      {
        value: "10y50o",
        label: "10 Year +50%",
        eliteOnly: false
      },
      {
        value: "10y500o",
        label: "10 Year +500%",
        eliteOnly: false
      },
      {
        value: "10y10u",
        label: "10 Year -10%",
        eliteOnly: false
      },
      {
        value: "10y20u",
        label: "10 Year -20%",
        eliteOnly: false
      },
      {
        value: "10y30u",
        label: "10 Year -30%",
        eliteOnly: false
      },
      {
        value: "10y50u",
        label: "10 Year -50%",
        eliteOnly: false
      },
      {
        value: "10y75u",
        label: "10 Year -75%",
        eliteOnly: false
      },
      {
        value: "10y90u",
        label: "10 Year -90%",
        eliteOnly: false
      },
      {
        value: "10ydown",
        label: "10 Year Down",
        eliteOnly: false
      },
      {
        value: "10yup",
        label: "10 Year Up",
        eliteOnly: false
      },
      {
        value: "3y10o",
        label: "3 Year +10%",
        eliteOnly: false
      },
      {
        value: "3y100o",
        label: "3 Year +100%",
        eliteOnly: false
      },
      {
        value: "3y1000o",
        label: "3 Year +1000%",
        eliteOnly: false
      },
      {
        value: "3y20o",
        label: "3 Year +20%",
        eliteOnly: false
      },
      {
        value: "3y200o",
        label: "3 Year +200%",
        eliteOnly: false
      },
      {
        value: "3y30o",
        label: "3 Year +30%",
        eliteOnly: false
      },
      {
        value: "3y300o",
        label: "3 Year +300%",
        eliteOnly: false
      },
      {
        value: "3y50o",
        label: "3 Year +50%",
        eliteOnly: false
      },
      {
        value: "3y500o",
        label: "3 Year +500%",
        eliteOnly: false
      },
      {
        value: "3y10u",
        label: "3 Year -10%",
        eliteOnly: false
      },
      {
        value: "3y20u",
        label: "3 Year -20%",
        eliteOnly: false
      },
      {
        value: "3y30u",
        label: "3 Year -30%",
        eliteOnly: false
      },
      {
        value: "3y50u",
        label: "3 Year -50%",
        eliteOnly: false
      },
      {
        value: "3y75u",
        label: "3 Year -75%",
        eliteOnly: false
      },
      {
        value: "3y90u",
        label: "3 Year -90%",
        eliteOnly: false
      },
      {
        value: "3ydown",
        label: "3 Year Down",
        eliteOnly: false
      },
      {
        value: "3yup",
        label: "3 Year Up",
        eliteOnly: false
      },
      {
        value: "5y10o",
        label: "5 Year +10%",
        eliteOnly: false
      },
      {
        value: "5y100o",
        label: "5 Year +100%",
        eliteOnly: false
      },
      {
        value: "5y1000o",
        label: "5 Year +1000%",
        eliteOnly: false
      },
      {
        value: "5y20o",
        label: "5 Year +20%",
        eliteOnly: false
      },
      {
        value: "5y200o",
        label: "5 Year +200%",
        eliteOnly: false
      },
      {
        value: "5y30o",
        label: "5 Year +30%",
        eliteOnly: false
      },
      {
        value: "5y300o",
        label: "5 Year +300%",
        eliteOnly: false
      },
      {
        value: "5y50o",
        label: "5 Year +50%",
        eliteOnly: false
      },
      {
        value: "5y500o",
        label: "5 Year +500%",
        eliteOnly: false
      },
      {
        value: "5y10u",
        label: "5 Year -10%",
        eliteOnly: false
      },
      {
        value: "5y20u",
        label: "5 Year -20%",
        eliteOnly: false
      },
      {
        value: "5y30u",
        label: "5 Year -30%",
        eliteOnly: false
      },
      {
        value: "5y50u",
        label: "5 Year -50%",
        eliteOnly: false
      },
      {
        value: "5y75u",
        label: "5 Year -75%",
        eliteOnly: false
      },
      {
        value: "5y90u",
        label: "5 Year -90%",
        eliteOnly: false
      },
      {
        value: "5ydown",
        label: "5 Year Down",
        eliteOnly: false
      },
      {
        value: "5yup",
        label: "5 Year Up",
        eliteOnly: false
      },
      {
        value: "26w10o",
        label: "Half +10%",
        eliteOnly: false
      },
      {
        value: "26w100o",
        label: "Half +100%",
        eliteOnly: false
      },
      {
        value: "26w20o",
        label: "Half +20%",
        eliteOnly: false
      },
      {
        value: "26w30o",
        label: "Half +30%",
        eliteOnly: false
      },
      {
        value: "26w50o",
        label: "Half +50%",
        eliteOnly: false
      },
      {
        value: "26w10u",
        label: "Half -10%",
        eliteOnly: false
      },
      {
        value: "26w20u",
        label: "Half -20%",
        eliteOnly: false
      },
      {
        value: "26w30u",
        label: "Half -30%",
        eliteOnly: false
      },
      {
        value: "26w50u",
        label: "Half -50%",
        eliteOnly: false
      },
      {
        value: "26w75u",
        label: "Half -75%",
        eliteOnly: false
      },
      {
        value: "26wdown",
        label: "Half Down",
        eliteOnly: false
      },
      {
        value: "26wup",
        label: "Half Up",
        eliteOnly: false
      },
      {
        value: "4w10o",
        label: "Month +10%",
        eliteOnly: false
      },
      {
        value: "4w20o",
        label: "Month +20%",
        eliteOnly: false
      },
      {
        value: "4w30o",
        label: "Month +30%",
        eliteOnly: false
      },
      {
        value: "4w50o",
        label: "Month +50%",
        eliteOnly: false
      },
      {
        value: "4w10u",
        label: "Month -10%",
        eliteOnly: false
      },
      {
        value: "4w20u",
        label: "Month -20%",
        eliteOnly: false
      },
      {
        value: "4w30u",
        label: "Month -30%",
        eliteOnly: false
      },
      {
        value: "4w50u",
        label: "Month -50%",
        eliteOnly: false
      },
      {
        value: "4wdown",
        label: "Month Down",
        eliteOnly: false
      },
      {
        value: "4wup",
        label: "Month Up",
        eliteOnly: false
      },
      {
        value: "13w10o",
        label: "Quarter +10%",
        eliteOnly: false
      },
      {
        value: "13w20o",
        label: "Quarter +20%",
        eliteOnly: false
      },
      {
        value: "13w30o",
        label: "Quarter +30%",
        eliteOnly: false
      },
      {
        value: "13w50o",
        label: "Quarter +50%",
        eliteOnly: false
      },
      {
        value: "13w10u",
        label: "Quarter -10%",
        eliteOnly: false
      },
      {
        value: "13w20u",
        label: "Quarter -20%",
        eliteOnly: false
      },
      {
        value: "13w30u",
        label: "Quarter -30%",
        eliteOnly: false
      },
      {
        value: "13w50u",
        label: "Quarter -50%",
        eliteOnly: false
      },
      {
        value: "13wdown",
        label: "Quarter Down",
        eliteOnly: false
      },
      {
        value: "13wup",
        label: "Quarter Up",
        eliteOnly: false
      },
      {
        value: "d10o",
        label: "Today +10%",
        eliteOnly: false
      },
      {
        value: "d15o",
        label: "Today +15%",
        eliteOnly: false
      },
      {
        value: "d5o",
        label: "Today +5%",
        eliteOnly: false
      },
      {
        value: "d10u",
        label: "Today -10%",
        eliteOnly: false
      },
      {
        value: "d15u",
        label: "Today -15%",
        eliteOnly: false
      },
      {
        value: "d5u",
        label: "Today -5%",
        eliteOnly: false
      },
      {
        value: "ddown",
        label: "Today Down",
        eliteOnly: false
      },
      {
        value: "dup",
        label: "Today Up",
        eliteOnly: false
      },
      {
        value: "1w10o",
        label: "Week +10%",
        eliteOnly: false
      },
      {
        value: "1w20o",
        label: "Week +20%",
        eliteOnly: false
      },
      {
        value: "1w30o",
        label: "Week +30%",
        eliteOnly: false
      },
      {
        value: "1w10u",
        label: "Week -10%",
        eliteOnly: false
      },
      {
        value: "1w20u",
        label: "Week -20%",
        eliteOnly: false
      },
      {
        value: "1w30u",
        label: "Week -30%",
        eliteOnly: false
      },
      {
        value: "1wdown",
        label: "Week Down",
        eliteOnly: false
      },
      {
        value: "1wup",
        label: "Week Up",
        eliteOnly: false
      },
      {
        value: "ytd10o",
        label: "YTD +10%",
        eliteOnly: false
      },
      {
        value: "ytd100o",
        label: "YTD +100%",
        eliteOnly: false
      },
      {
        value: "ytd20o",
        label: "YTD +20%",
        eliteOnly: false
      },
      {
        value: "ytd30o",
        label: "YTD +30%",
        eliteOnly: false
      },
      {
        value: "ytd5o",
        label: "YTD +5%",
        eliteOnly: false
      },
      {
        value: "ytd50o",
        label: "YTD +50%",
        eliteOnly: false
      },
      {
        value: "ytd10u",
        label: "YTD -10%",
        eliteOnly: false
      },
      {
        value: "ytd20u",
        label: "YTD -20%",
        eliteOnly: false
      },
      {
        value: "ytd30u",
        label: "YTD -30%",
        eliteOnly: false
      },
      {
        value: "ytd5u",
        label: "YTD -5%",
        eliteOnly: false
      },
      {
        value: "ytd50u",
        label: "YTD -50%",
        eliteOnly: false
      },
      {
        value: "ytd75u",
        label: "YTD -75%",
        eliteOnly: false
      },
      {
        value: "ytddown",
        label: "YTD Down",
        eliteOnly: false
      },
      {
        value: "ytdup",
        label: "YTD Up",
        eliteOnly: false
      },
      {
        value: "52w10o",
        label: "Year +10%",
        eliteOnly: false
      },
      {
        value: "52w100o",
        label: "Year +100%",
        eliteOnly: false
      },
      {
        value: "52w20o",
        label: "Year +20%",
        eliteOnly: false
      },
      {
        value: "52w200o",
        label: "Year +200%",
        eliteOnly: false
      },
      {
        value: "52w30o",
        label: "Year +30%",
        eliteOnly: false
      },
      {
        value: "52w300o",
        label: "Year +300%",
        eliteOnly: false
      },
      {
        value: "52w50o",
        label: "Year +50%",
        eliteOnly: false
      },
      {
        value: "52w500o",
        label: "Year +500%",
        eliteOnly: false
      },
      {
        value: "52w10u",
        label: "Year -10%",
        eliteOnly: false
      },
      {
        value: "52w20u",
        label: "Year -20%",
        eliteOnly: false
      },
      {
        value: "52w30u",
        label: "Year -30%",
        eliteOnly: false
      },
      {
        value: "52w50u",
        label: "Year -50%",
        eliteOnly: false
      },
      {
        value: "52w75u",
        label: "Year -75%",
        eliteOnly: false
      },
      {
        value: "52wdown",
        label: "Year Down",
        eliteOnly: false
      },
      {
        value: "52wup",
        label: "Year Up",
        eliteOnly: false
      },
      {
        value: "custom_subscription",
        label: "Intraday (Elite only)",
        eliteOnly: true
      }
    ]
  },
  ta_rsi: {
    key: "ta_rsi",
    label: "RSI (14)",
    dataFilter: "ta_rsi",
    groups: [
      "technical",
      "all"
    ],
    options: [
      {
        value: "",
        label: "Any",
        eliteOnly: false
      },
      {
        value: "nob50",
        label: "Not Overbought (<50)",
        eliteOnly: false
      },
      {
        value: "nob60",
        label: "Not Overbought (<60)",
        eliteOnly: false
      },
      {
        value: "nos40",
        label: "Not Oversold (>40)",
        eliteOnly: false
      },
      {
        value: "nos50",
        label: "Not Oversold (>50)",
        eliteOnly: false
      },
      {
        value: "ob60",
        label: "Overbought (60)",
        eliteOnly: false
      },
      {
        value: "ob70",
        label: "Overbought (70)",
        eliteOnly: false
      },
      {
        value: "ob80",
        label: "Overbought (80)",
        eliteOnly: false
      },
      {
        value: "ob90",
        label: "Overbought (90)",
        eliteOnly: false
      },
      {
        value: "os10",
        label: "Oversold (10)",
        eliteOnly: false
      },
      {
        value: "os20",
        label: "Oversold (20)",
        eliteOnly: false
      },
      {
        value: "os30",
        label: "Oversold (30)",
        eliteOnly: false
      },
      {
        value: "os40",
        label: "Oversold (40)",
        eliteOnly: false
      },
      {
        value: "custom_subscription",
        label: "Custom (Elite only)",
        eliteOnly: true
      }
    ]
  },
  ta_sma20: {
    key: "ta_sma20",
    label: "20-Day Simple Moving Average",
    dataFilter: "ta_sma20",
    groups: [
      "technical",
      "all"
    ],
    options: [
      {
        value: "",
        label: "Any",
        eliteOnly: false
      },
      {
        value: "pa10",
        label: "Price 10% above SMA20",
        eliteOnly: false
      },
      {
        value: "pb10",
        label: "Price 10% below SMA20",
        eliteOnly: false
      },
      {
        value: "pa20",
        label: "Price 20% above SMA20",
        eliteOnly: false
      },
      {
        value: "pb20",
        label: "Price 20% below SMA20",
        eliteOnly: false
      },
      {
        value: "pa30",
        label: "Price 30% above SMA20",
        eliteOnly: false
      },
      {
        value: "pb30",
        label: "Price 30% below SMA20",
        eliteOnly: false
      },
      {
        value: "pa40",
        label: "Price 40% above SMA20",
        eliteOnly: false
      },
      {
        value: "pb40",
        label: "Price 40% below SMA20",
        eliteOnly: false
      },
      {
        value: "pa50",
        label: "Price 50% above SMA20",
        eliteOnly: false
      },
      {
        value: "pb50",
        label: "Price 50% below SMA20",
        eliteOnly: false
      },
      {
        value: "pa",
        label: "Price above SMA20",
        eliteOnly: false
      },
      {
        value: "pb",
        label: "Price below SMA20",
        eliteOnly: false
      },
      {
        value: "pc",
        label: "Price crossed SMA20",
        eliteOnly: false
      },
      {
        value: "pca",
        label: "Price crossed SMA20 above",
        eliteOnly: false
      },
      {
        value: "pcb",
        label: "Price crossed SMA20 below",
        eliteOnly: false
      },
      {
        value: "sa200",
        label: "SMA20 above SMA200",
        eliteOnly: false
      },
      {
        value: "sa50",
        label: "SMA20 above SMA50",
        eliteOnly: false
      },
      {
        value: "sb200",
        label: "SMA20 below SMA200",
        eliteOnly: false
      },
      {
        value: "sb50",
        label: "SMA20 below SMA50",
        eliteOnly: false
      },
      {
        value: "cross200",
        label: "SMA20 crossed SMA200",
        eliteOnly: false
      },
      {
        value: "cross200a",
        label: "SMA20 crossed SMA200 above",
        eliteOnly: false
      },
      {
        value: "cross200b",
        label: "SMA20 crossed SMA200 below",
        eliteOnly: false
      },
      {
        value: "cross50",
        label: "SMA20 crossed SMA50",
        eliteOnly: false
      },
      {
        value: "cross50a",
        label: "SMA20 crossed SMA50 above",
        eliteOnly: false
      },
      {
        value: "cross50b",
        label: "SMA20 crossed SMA50 below",
        eliteOnly: false
      },
      {
        value: "custom_subscription",
        label: "Custom (Elite only)",
        eliteOnly: true
      }
    ]
  },
  ta_sma200: {
    key: "ta_sma200",
    label: "200-Day Simple Moving Average",
    dataFilter: "ta_sma200",
    groups: [
      "technical",
      "all"
    ],
    options: [
      {
        value: "",
        label: "Any",
        eliteOnly: false
      },
      {
        value: "pa10",
        label: "Price 10% above SMA200",
        eliteOnly: false
      },
      {
        value: "pb10",
        label: "Price 10% below SMA200",
        eliteOnly: false
      },
      {
        value: "pa100",
        label: "Price 100% above SMA200",
        eliteOnly: false
      },
      {
        value: "pa20",
        label: "Price 20% above SMA200",
        eliteOnly: false
      },
      {
        value: "pb20",
        label: "Price 20% below SMA200",
        eliteOnly: false
      },
      {
        value: "pa30",
        label: "Price 30% above SMA200",
        eliteOnly: false
      },
      {
        value: "pb30",
        label: "Price 30% below SMA200",
        eliteOnly: false
      },
      {
        value: "pa40",
        label: "Price 40% above SMA200",
        eliteOnly: false
      },
      {
        value: "pb40",
        label: "Price 40% below SMA200",
        eliteOnly: false
      },
      {
        value: "pa50",
        label: "Price 50% above SMA200",
        eliteOnly: false
      },
      {
        value: "pb50",
        label: "Price 50% below SMA200",
        eliteOnly: false
      },
      {
        value: "pa60",
        label: "Price 60% above SMA200",
        eliteOnly: false
      },
      {
        value: "pb60",
        label: "Price 60% below SMA200",
        eliteOnly: false
      },
      {
        value: "pa70",
        label: "Price 70% above SMA200",
        eliteOnly: false
      },
      {
        value: "pb70",
        label: "Price 70% below SMA200",
        eliteOnly: false
      },
      {
        value: "pa80",
        label: "Price 80% above SMA200",
        eliteOnly: false
      },
      {
        value: "pb80",
        label: "Price 80% below SMA200",
        eliteOnly: false
      },
      {
        value: "pa90",
        label: "Price 90% above SMA200",
        eliteOnly: false
      },
      {
        value: "pb90",
        label: "Price 90% below SMA200",
        eliteOnly: false
      },
      {
        value: "pa",
        label: "Price above SMA200",
        eliteOnly: false
      },
      {
        value: "pb",
        label: "Price below SMA200",
        eliteOnly: false
      },
      {
        value: "pc",
        label: "Price crossed SMA200",
        eliteOnly: false
      },
      {
        value: "pca",
        label: "Price crossed SMA200 above",
        eliteOnly: false
      },
      {
        value: "pcb",
        label: "Price crossed SMA200 below",
        eliteOnly: false
      },
      {
        value: "sa20",
        label: "SMA200 above SMA20",
        eliteOnly: false
      },
      {
        value: "sa50",
        label: "SMA200 above SMA50",
        eliteOnly: false
      },
      {
        value: "sb20",
        label: "SMA200 below SMA20",
        eliteOnly: false
      },
      {
        value: "sb50",
        label: "SMA200 below SMA50",
        eliteOnly: false
      },
      {
        value: "cross20",
        label: "SMA200 crossed SMA20",
        eliteOnly: false
      },
      {
        value: "cross20a",
        label: "SMA200 crossed SMA20 above",
        eliteOnly: false
      },
      {
        value: "cross20b",
        label: "SMA200 crossed SMA20 below",
        eliteOnly: false
      },
      {
        value: "cross50",
        label: "SMA200 crossed SMA50",
        eliteOnly: false
      },
      {
        value: "cross50a",
        label: "SMA200 crossed SMA50 above",
        eliteOnly: false
      },
      {
        value: "cross50b",
        label: "SMA200 crossed SMA50 below",
        eliteOnly: false
      },
      {
        value: "custom_subscription",
        label: "Custom (Elite only)",
        eliteOnly: true
      }
    ]
  },
  ta_sma50: {
    key: "ta_sma50",
    label: "50-Day Simple Moving Average",
    dataFilter: "ta_sma50",
    groups: [
      "technical",
      "all"
    ],
    options: [
      {
        value: "",
        label: "Any",
        eliteOnly: false
      },
      {
        value: "pa10",
        label: "Price 10% above SMA50",
        eliteOnly: false
      },
      {
        value: "pb10",
        label: "Price 10% below SMA50",
        eliteOnly: false
      },
      {
        value: "pa20",
        label: "Price 20% above SMA50",
        eliteOnly: false
      },
      {
        value: "pb20",
        label: "Price 20% below SMA50",
        eliteOnly: false
      },
      {
        value: "pa30",
        label: "Price 30% above SMA50",
        eliteOnly: false
      },
      {
        value: "pb30",
        label: "Price 30% below SMA50",
        eliteOnly: false
      },
      {
        value: "pa40",
        label: "Price 40% above SMA50",
        eliteOnly: false
      },
      {
        value: "pb40",
        label: "Price 40% below SMA50",
        eliteOnly: false
      },
      {
        value: "pa50",
        label: "Price 50% above SMA50",
        eliteOnly: false
      },
      {
        value: "pb50",
        label: "Price 50% below SMA50",
        eliteOnly: false
      },
      {
        value: "pa",
        label: "Price above SMA50",
        eliteOnly: false
      },
      {
        value: "pb",
        label: "Price below SMA50",
        eliteOnly: false
      },
      {
        value: "pc",
        label: "Price crossed SMA50",
        eliteOnly: false
      },
      {
        value: "pca",
        label: "Price crossed SMA50 above",
        eliteOnly: false
      },
      {
        value: "pcb",
        label: "Price crossed SMA50 below",
        eliteOnly: false
      },
      {
        value: "sa20",
        label: "SMA50 above SMA20",
        eliteOnly: false
      },
      {
        value: "sa200",
        label: "SMA50 above SMA200",
        eliteOnly: false
      },
      {
        value: "sb20",
        label: "SMA50 below SMA20",
        eliteOnly: false
      },
      {
        value: "sb200",
        label: "SMA50 below SMA200",
        eliteOnly: false
      },
      {
        value: "cross20",
        label: "SMA50 crossed SMA20",
        eliteOnly: false
      },
      {
        value: "cross20a",
        label: "SMA50 crossed SMA20 above",
        eliteOnly: false
      },
      {
        value: "cross20b",
        label: "SMA50 crossed SMA20 below",
        eliteOnly: false
      },
      {
        value: "cross200",
        label: "SMA50 crossed SMA200",
        eliteOnly: false
      },
      {
        value: "cross200a",
        label: "SMA50 crossed SMA200 above",
        eliteOnly: false
      },
      {
        value: "cross200b",
        label: "SMA50 crossed SMA200 below",
        eliteOnly: false
      },
      {
        value: "custom_subscription",
        label: "Custom (Elite only)",
        eliteOnly: true
      }
    ]
  },
  ta_volatility: {
    key: "ta_volatility",
    label: "Volatility",
    dataFilter: "ta_volatility",
    groups: [
      "technical",
      "all"
    ],
    options: [
      {
        value: "",
        label: "Any",
        eliteOnly: false
      },
      {
        value: "mo10",
        label: "Month - Over 10%",
        eliteOnly: false
      },
      {
        value: "mo12",
        label: "Month - Over 12%",
        eliteOnly: false
      },
      {
        value: "mo15",
        label: "Month - Over 15%",
        eliteOnly: false
      },
      {
        value: "mo2",
        label: "Month - Over 2%",
        eliteOnly: false
      },
      {
        value: "mo3",
        label: "Month - Over 3%",
        eliteOnly: false
      },
      {
        value: "mo4",
        label: "Month - Over 4%",
        eliteOnly: false
      },
      {
        value: "mo5",
        label: "Month - Over 5%",
        eliteOnly: false
      },
      {
        value: "mo6",
        label: "Month - Over 6%",
        eliteOnly: false
      },
      {
        value: "mo7",
        label: "Month - Over 7%",
        eliteOnly: false
      },
      {
        value: "mo8",
        label: "Month - Over 8%",
        eliteOnly: false
      },
      {
        value: "mo9",
        label: "Month - Over 9%",
        eliteOnly: false
      },
      {
        value: "wo10",
        label: "Week - Over 10%",
        eliteOnly: false
      },
      {
        value: "wo12",
        label: "Week - Over 12%",
        eliteOnly: false
      },
      {
        value: "wo15",
        label: "Week - Over 15%",
        eliteOnly: false
      },
      {
        value: "wo2",
        label: "Week - Over 2%",
        eliteOnly: false
      },
      {
        value: "wo3",
        label: "Week - Over 3%",
        eliteOnly: false
      },
      {
        value: "wo4",
        label: "Week - Over 4%",
        eliteOnly: false
      },
      {
        value: "wo5",
        label: "Week - Over 5%",
        eliteOnly: false
      },
      {
        value: "wo6",
        label: "Week - Over 6%",
        eliteOnly: false
      },
      {
        value: "wo7",
        label: "Week - Over 7%",
        eliteOnly: false
      },
      {
        value: "wo8",
        label: "Week - Over 8%",
        eliteOnly: false
      },
      {
        value: "wo9",
        label: "Week - Over 9%",
        eliteOnly: false
      },
      {
        value: "custom_subscription",
        label: "Custom (Elite only)",
        eliteOnly: true
      }
    ]
  },
  targetPrice: {
    key: "targetPrice",
    label: "Target Price",
    dataFilter: "targetprice",
    groups: [
      "descriptive",
      "all"
    ],
    options: [
      {
        value: "",
        label: "Any",
        eliteOnly: false
      },
      {
        value: "a10",
        label: "10% Above Price",
        eliteOnly: false
      },
      {
        value: "b10",
        label: "10% Below Price",
        eliteOnly: false
      },
      {
        value: "a20",
        label: "20% Above Price",
        eliteOnly: false
      },
      {
        value: "b20",
        label: "20% Below Price",
        eliteOnly: false
      },
      {
        value: "a30",
        label: "30% Above Price",
        eliteOnly: false
      },
      {
        value: "b30",
        label: "30% Below Price",
        eliteOnly: false
      },
      {
        value: "a40",
        label: "40% Above Price",
        eliteOnly: false
      },
      {
        value: "b40",
        label: "40% Below Price",
        eliteOnly: false
      },
      {
        value: "a5",
        label: "5% Above Price",
        eliteOnly: false
      },
      {
        value: "b5",
        label: "5% Below Price",
        eliteOnly: false
      },
      {
        value: "a50",
        label: "50% Above Price",
        eliteOnly: false
      },
      {
        value: "b50",
        label: "50% Below Price",
        eliteOnly: false
      },
      {
        value: "above",
        label: "Above Price",
        eliteOnly: false
      },
      {
        value: "below",
        label: "Below Price",
        eliteOnly: false
      },
      {
        value: "custom_subscription",
        label: "Custom (Elite only)",
        eliteOnly: true
      }
    ]
  },
  theme: {
    key: "theme",
    label: "Theme",
    dataFilter: "theme",
    groups: [
      "descriptive",
      "all"
    ],
    options: [
      {
        value: "",
        label: "Any",
        eliteOnly: false
      },
      {
        value: "agingpopulationlongevity",
        label: "Aging Population & Longevity",
        eliteOnly: false
      },
      {
        value: "agriculturefoodtech",
        label: "Agriculture & FoodTech",
        eliteOnly: false
      },
      {
        value: "artificialintelligence",
        label: "Artificial Intelligence",
        eliteOnly: false
      },
      {
        value: "autonomoussystems",
        label: "Autonomous Systems",
        eliteOnly: false
      },
      {
        value: "bigdata",
        label: "Big Data",
        eliteOnly: false
      },
      {
        value: "biometrics",
        label: "Biometrics",
        eliteOnly: false
      },
      {
        value: "cloudcomputing",
        label: "Cloud Computing",
        eliteOnly: false
      },
      {
        value: "commoditiesagriculture",
        label: "Commodities - Agriculture",
        eliteOnly: false
      },
      {
        value: "commoditiesenergy",
        label: "Commodities - Energy",
        eliteOnly: false
      },
      {
        value: "commoditiesmetals",
        label: "Commodities - Metals",
        eliteOnly: false
      },
      {
        value: "consumergoods",
        label: "Consumer Goods",
        eliteOnly: false
      },
      {
        value: "cryptoblockchain",
        label: "Crypto & Blockchain",
        eliteOnly: false
      },
      {
        value: "cybersecurity",
        label: "Cybersecurity",
        eliteOnly: false
      },
      {
        value: "defenseaerospace",
        label: "Defense & Aerospace",
        eliteOnly: false
      },
      {
        value: "digitalentertainment",
        label: "Digital Entertainment",
        eliteOnly: false
      },
      {
        value: "ecommerce",
        label: "E-commerce",
        eliteOnly: false
      },
      {
        value: "educationtechnology",
        label: "Education Technology",
        eliteOnly: false
      },
      {
        value: "electricvehicles",
        label: "Electric Vehicles",
        eliteOnly: false
      },
      {
        value: "energyrenewable",
        label: "Energy - Renewable",
        eliteOnly: false
      },
      {
        value: "energytraditional",
        label: "Energy - Traditional",
        eliteOnly: false
      },
      {
        value: "environmentalsustainability",
        label: "Environmental Sustainability",
        eliteOnly: false
      },
      {
        value: "fintech",
        label: "FinTech",
        eliteOnly: false
      },
      {
        value: "hardware",
        label: "Hardware",
        eliteOnly: false
      },
      {
        value: "healthcarebiotech",
        label: "Healthcare & Biotech",
        eliteOnly: false
      },
      {
        value: "healthyfoodnutrition",
        label: "Healthy Food & Nutrition",
        eliteOnly: false
      },
      {
        value: "industrialautomation",
        label: "Industrial Automation",
        eliteOnly: false
      },
      {
        value: "internetofthings",
        label: "Internet of Things",
        eliteOnly: false
      },
      {
        value: "nanotechnology",
        label: "Nanotechnology",
        eliteOnly: false
      },
      {
        value: "quantumcomputing",
        label: "Quantum Computing",
        eliteOnly: false
      },
      {
        value: "realestatereits",
        label: "Real Estate & REITs",
        eliteOnly: false
      },
      {
        value: "robotics",
        label: "Robotics",
        eliteOnly: false
      },
      {
        value: "semiconductors",
        label: "Semiconductors",
        eliteOnly: false
      },
      {
        value: "smarthome",
        label: "Smart Home",
        eliteOnly: false
      },
      {
        value: "socialmedia",
        label: "Social Media",
        eliteOnly: false
      },
      {
        value: "software",
        label: "Software",
        eliteOnly: false
      },
      {
        value: "spacetech",
        label: "Space Tech",
        eliteOnly: false
      },
      {
        value: "telecommunications",
        label: "Telecommunications",
        eliteOnly: false
      },
      {
        value: "transportationlogistics",
        label: "Transportation & Logistics",
        eliteOnly: false
      },
      {
        value: "virtualaugmentedreality",
        label: "Virtual & Augmented Reality",
        eliteOnly: false
      },
      {
        value: "wearables",
        label: "Wearables",
        eliteOnly: false
      },
      {
        value: "custom_subscription",
        label: "Custom (Elite only)",
        eliteOnly: true
      }
    ]
  },
  trades: {
    key: "trades",
    label: "Trades",
    dataFilter: "sh_trades",
    groups: [
      "descriptive",
      "all"
    ],
    options: [
      {
        value: "custom_subscription",
        label: "Elite only",
        eliteOnly: true
      }
    ]
  }
};

export const SCREENER_FILTER_GROUP_LAYOUTS: Record<ScreenerFilterGroup, Array<Array<{ key: string; label: string }>>> = {
  descriptive: [
    [
      {
        key: "exchange",
        label: "Exchange"
      },
      {
        key: "index",
        label: "Index"
      },
      {
        key: "sector",
        label: "Sector"
      },
      {
        key: "industry",
        label: "Industry"
      },
      {
        key: "country",
        label: "Country"
      }
    ],
    [
      {
        key: "marketCap",
        label: "Market Cap."
      },
      {
        key: "dividendYield",
        label: "Dividend Yield"
      },
      {
        key: "shortFloat",
        label: "Short Float"
      },
      {
        key: "analystRecom",
        label: "Analyst Recom."
      },
      {
        key: "optionShort",
        label: "Option/Short"
      }
    ],
    [
      {
        key: "earningsDate",
        label: "Earnings Date"
      },
      {
        key: "avgVolume",
        label: "Average Volume"
      },
      {
        key: "relVolume",
        label: "Relative Volume"
      },
      {
        key: "currentVolume",
        label: "Current Volume"
      },
      {
        key: "trades",
        label: "Trades"
      }
    ],
    [
      {
        key: "priceBand",
        label: "Price $"
      },
      {
        key: "targetPrice",
        label: "Target Price"
      },
      {
        key: "ipoDate",
        label: "IPO Date"
      },
      {
        key: "sharesOutstanding",
        label: "Shares Outstanding"
      },
      {
        key: "float",
        label: "Float"
      }
    ],
    [
      {
        key: "theme",
        label: "Theme"
      },
      {
        key: "subTheme",
        label: "Sub-theme"
      }
    ]
  ],
  fundamental: [
    [
      {
        key: "fa_pe",
        label: "P/E"
      },
      {
        key: "fa_fpe",
        label: "Forward P/E"
      },
      {
        key: "fa_peg",
        label: "PEG"
      },
      {
        key: "fa_ps",
        label: "P/S"
      },
      {
        key: "fa_pb",
        label: "P/B"
      }
    ],
    [
      {
        key: "fa_pc",
        label: "Price/Cash"
      },
      {
        key: "fa_pfcf",
        label: "Price/Free Cash Flow"
      },
      {
        key: "fa_evebitda",
        label: "EV/EBITDA"
      },
      {
        key: "fa_evsales",
        label: "EV/Sales"
      },
      {
        key: "fa_divgrowth",
        label: "Dividend Growth"
      }
    ],
    [
      {
        key: "fa_epsyoy",
        label: "EPS Growth This Year"
      },
      {
        key: "fa_epsyoy1",
        label: "EPS Growth Next Year"
      },
      {
        key: "fa_epsqoq",
        label: "EPS Growth Qtr Over Qtr"
      },
      {
        key: "fa_epsyoyttm",
        label: "EPS Growth TTM"
      },
      {
        key: "fa_eps3years",
        label: "EPS Growth Past 3 Years"
      }
    ],
    [
      {
        key: "fa_eps5years",
        label: "EPS Growth Past 5 Years"
      },
      {
        key: "fa_estltgrowth",
        label: "EPS Growth Next 5 Years"
      },
      {
        key: "fa_salesqoq",
        label: "Sales Growth Qtr Over Qtr"
      },
      {
        key: "fa_salesyoyttm",
        label: "Sales Growth TTM"
      },
      {
        key: "fa_sales3years",
        label: "Sales Growth Past 3 Years"
      }
    ],
    [
      {
        key: "fa_sales5years",
        label: "Sales Growth Past 5 Years"
      },
      {
        key: "fa_epsrev",
        label: "Earnings & Revenue Surprise"
      },
      {
        key: "fa_roa",
        label: "Return on Assets"
      },
      {
        key: "fa_roe",
        label: "Return on Equity"
      },
      {
        key: "fa_roi",
        label: "Return on Invested Capital"
      }
    ],
    [
      {
        key: "fa_curratio",
        label: "Current Ratio"
      },
      {
        key: "fa_quickratio",
        label: "Quick Ratio"
      },
      {
        key: "fa_ltdebteq",
        label: "LT Debt/Equity"
      },
      {
        key: "fa_debteq",
        label: "Debt/Equity"
      },
      {
        key: "fa_grossmargin",
        label: "Gross Margin"
      }
    ],
    [
      {
        key: "fa_opermargin",
        label: "Operating Margin"
      },
      {
        key: "fa_netmargin",
        label: "Net Profit Margin"
      },
      {
        key: "fa_payoutratio",
        label: "Payout Ratio"
      },
      {
        key: "sh_insiderown",
        label: "Insider Ownership"
      },
      {
        key: "sh_insidertrans",
        label: "Insider Transactions"
      }
    ],
    [
      {
        key: "sh_instown",
        label: "Institutional Ownership"
      },
      {
        key: "sh_insttrans",
        label: "Institutional Transactions"
      }
    ]
  ],
  technical: [
    [
      {
        key: "ta_perf",
        label: "Performance"
      },
      {
        key: "ta_perf2",
        label: "Performance 2"
      },
      {
        key: "ta_volatility",
        label: "Volatility"
      },
      {
        key: "ta_rsi",
        label: "RSI (14)"
      },
      {
        key: "ta_gap",
        label: "Gap"
      }
    ],
    [
      {
        key: "ta_sma20",
        label: "20-Day Simple Moving Average"
      },
      {
        key: "ta_sma50",
        label: "50-Day Simple Moving Average"
      },
      {
        key: "ta_sma200",
        label: "200-Day Simple Moving Average"
      },
      {
        key: "ta_change",
        label: "Change"
      },
      {
        key: "ta_changeopen",
        label: "Change from Open"
      }
    ],
    [
      {
        key: "ta_highlow20d",
        label: "20-Day High/Low"
      },
      {
        key: "ta_highlow50d",
        label: "50-Day High/Low"
      },
      {
        key: "ta_highlow52w",
        label: "52-Week High/Low"
      },
      {
        key: "ta_alltime",
        label: "All-Time High/Low"
      },
      {
        key: "ta_pattern",
        label: "Pattern"
      }
    ],
    [
      {
        key: "ta_candlestick",
        label: "Candlestick"
      },
      {
        key: "ta_beta",
        label: "Beta"
      },
      {
        key: "ta_averagetruerange",
        label: "Average True Range"
      },
      {
        key: "ah_close",
        label: "After-Hours Close"
      },
      {
        key: "ah_change",
        label: "After-Hours Change"
      }
    ]
  ],
  all: [
    [
      {
        key: "exchange",
        label: "Exchange"
      },
      {
        key: "index",
        label: "Index"
      },
      {
        key: "sector",
        label: "Sector"
      },
      {
        key: "industry",
        label: "Industry"
      },
      {
        key: "country",
        label: "Country"
      }
    ],
    [
      {
        key: "marketCap",
        label: "Market Cap."
      },
      {
        key: "fa_pe",
        label: "P/E"
      },
      {
        key: "fa_fpe",
        label: "Forward P/E"
      },
      {
        key: "fa_peg",
        label: "PEG"
      },
      {
        key: "fa_ps",
        label: "P/S"
      }
    ],
    [
      {
        key: "fa_pb",
        label: "P/B"
      },
      {
        key: "fa_pc",
        label: "Price/Cash"
      },
      {
        key: "fa_pfcf",
        label: "Price/Free Cash Flow"
      },
      {
        key: "fa_evebitda",
        label: "EV/EBITDA"
      },
      {
        key: "fa_evsales",
        label: "EV/Sales"
      }
    ],
    [
      {
        key: "fa_divgrowth",
        label: "Dividend Growth"
      },
      {
        key: "fa_epsyoy",
        label: "EPS Growth This Year"
      },
      {
        key: "fa_epsyoy1",
        label: "EPS Growth Next Year"
      },
      {
        key: "fa_epsqoq",
        label: "EPS Growth Qtr Over Qtr"
      },
      {
        key: "fa_epsyoyttm",
        label: "EPS Growth TTM"
      }
    ],
    [
      {
        key: "fa_eps3years",
        label: "EPS Growth Past 3 Years"
      },
      {
        key: "fa_eps5years",
        label: "EPS Growth Past 5 Years"
      },
      {
        key: "fa_estltgrowth",
        label: "EPS Growth Next 5 Years"
      },
      {
        key: "fa_salesqoq",
        label: "Sales Growth Qtr Over Qtr"
      },
      {
        key: "fa_salesyoyttm",
        label: "Sales Growth TTM"
      }
    ],
    [
      {
        key: "fa_sales3years",
        label: "Sales Growth Past 3 Years"
      },
      {
        key: "fa_sales5years",
        label: "Sales Growth Past 5 Years"
      },
      {
        key: "fa_epsrev",
        label: "Earnings & Revenue Surprise"
      },
      {
        key: "dividendYield",
        label: "Dividend Yield"
      },
      {
        key: "fa_roa",
        label: "Return on Assets"
      }
    ],
    [
      {
        key: "fa_roe",
        label: "Return on Equity"
      },
      {
        key: "fa_roi",
        label: "Return on Invested Capital"
      },
      {
        key: "fa_curratio",
        label: "Current Ratio"
      },
      {
        key: "fa_quickratio",
        label: "Quick Ratio"
      },
      {
        key: "fa_ltdebteq",
        label: "LT Debt/Equity"
      }
    ],
    [
      {
        key: "fa_debteq",
        label: "Debt/Equity"
      },
      {
        key: "fa_grossmargin",
        label: "Gross Margin"
      },
      {
        key: "fa_opermargin",
        label: "Operating Margin"
      },
      {
        key: "fa_netmargin",
        label: "Net Profit Margin"
      },
      {
        key: "fa_payoutratio",
        label: "Payout Ratio"
      }
    ],
    [
      {
        key: "sh_insiderown",
        label: "Insider Ownership"
      },
      {
        key: "sh_insidertrans",
        label: "Insider Transactions"
      },
      {
        key: "sh_instown",
        label: "Institutional Ownership"
      },
      {
        key: "sh_insttrans",
        label: "Institutional Transactions"
      },
      {
        key: "shortFloat",
        label: "Short Float"
      }
    ],
    [
      {
        key: "analystRecom",
        label: "Analyst Recom."
      },
      {
        key: "optionShort",
        label: "Option/Short"
      },
      {
        key: "earningsDate",
        label: "Earnings Date"
      },
      {
        key: "ta_perf",
        label: "Performance"
      },
      {
        key: "ta_perf2",
        label: "Performance 2"
      }
    ],
    [
      {
        key: "ta_volatility",
        label: "Volatility"
      },
      {
        key: "ta_rsi",
        label: "RSI (14)"
      },
      {
        key: "ta_gap",
        label: "Gap"
      },
      {
        key: "ta_sma20",
        label: "20-Day Simple Moving Average"
      },
      {
        key: "ta_sma50",
        label: "50-Day Simple Moving Average"
      }
    ],
    [
      {
        key: "ta_sma200",
        label: "200-Day Simple Moving Average"
      },
      {
        key: "ta_change",
        label: "Change"
      },
      {
        key: "ta_changeopen",
        label: "Change from Open"
      },
      {
        key: "ta_highlow20d",
        label: "20-Day High/Low"
      },
      {
        key: "ta_highlow50d",
        label: "50-Day High/Low"
      }
    ],
    [
      {
        key: "ta_highlow52w",
        label: "52-Week High/Low"
      },
      {
        key: "ta_alltime",
        label: "All-Time High/Low"
      },
      {
        key: "ta_pattern",
        label: "Pattern"
      },
      {
        key: "ta_candlestick",
        label: "Candlestick"
      },
      {
        key: "ta_beta",
        label: "Beta"
      }
    ],
    [
      {
        key: "ta_averagetruerange",
        label: "Average True Range"
      },
      {
        key: "avgVolume",
        label: "Average Volume"
      },
      {
        key: "relVolume",
        label: "Relative Volume"
      },
      {
        key: "currentVolume",
        label: "Current Volume"
      },
      {
        key: "trades",
        label: "Trades"
      }
    ],
    [
      {
        key: "priceBand",
        label: "Price $"
      },
      {
        key: "targetPrice",
        label: "Target Price"
      },
      {
        key: "ipoDate",
        label: "IPO Date"
      },
      {
        key: "sharesOutstanding",
        label: "Shares Outstanding"
      },
      {
        key: "float",
        label: "Float"
      }
    ],
    [
      {
        key: "theme",
        label: "Theme"
      },
      {
        key: "subTheme",
        label: "Sub-theme"
      },
      {
        key: "ah_close",
        label: "After-Hours Close"
      },
      {
        key: "ah_change",
        label: "After-Hours Change"
      },
      {
        key: "news_date",
        label: "Latest News"
      }
    ],
    [
      {
        key: "etf_category",
        label: "Single Category"
      },
      {
        key: "etf_assettype",
        label: "Asset Type"
      },
      {
        key: "etf_sponsor",
        label: "Sponsor"
      },
      {
        key: "etf_netexpense",
        label: "Net Expense Ratio"
      }
    ],
    [
      {
        key: "etf_fundflows",
        label: "Net Fund Flows"
      },
      {
        key: "etf_return",
        label: "Annualized Return"
      },
      {
        key: "etf_tags",
        label: "Tags"
      }
    ]
  ],
  etf: [
    [
      {
        key: "etf_category",
        label: "Single Category"
      },
      {
        key: "etf_assettype",
        label: "Asset Type"
      },
      {
        key: "etf_etftype",
        label: "ETF Type"
      },
      {
        key: "etf_sectortheme",
        label: "Sector/Theme"
      },
      {
        key: "etf_region",
        label: "Region"
      }
    ],
    [
      {
        key: "etf_bondtype",
        label: "Bond Type"
      },
      {
        key: "etf_bondmaturity",
        label: "Average Maturity"
      },
      {
        key: "etf_quanttype",
        label: "Quant Type"
      },
      {
        key: "etf_commoditytype",
        label: "Commodity Type"
      },
      {
        key: "etf_esgtype",
        label: "ESG Type"
      }
    ],
    [
      {
        key: "etf_dividendtype",
        label: "Dividend Type"
      },
      {
        key: "etf_structuretype",
        label: "Structure Type"
      },
      {
        key: "etf_active",
        label: "Active/Passive"
      },
      {
        key: "etf_inverse",
        label: "Inverse/Leveraged"
      },
      {
        key: "etf_growthvalue",
        label: "Growth/Value"
      }
    ],
    [
      {
        key: "etf_mktcap",
        label: "Market Cap. (ETF)"
      },
      {
        key: "etf_developed",
        label: "Developed/Emerging"
      },
      {
        key: "etf_currency",
        label: "Currency"
      },
      {
        key: "etf_indexweight",
        label: "Index Weighting"
      },
      {
        key: "etf_sponsor",
        label: "Sponsor"
      }
    ],
    [
      {
        key: "etf_netexpense",
        label: "Net Expense Ratio"
      },
      {
        key: "etf_fundflows",
        label: "Net Fund Flows"
      },
      {
        key: "etf_return",
        label: "Annualized Return"
      },
      {
        key: "etf_nav",
        label: "Net Asset Value%"
      },
      {
        key: "etf_tags",
        label: "Tags"
      }
    ]
  ],
  news: [
    [
      {
        key: "news_date",
        label: "Latest News"
      }
    ]
  ]
};

export const SCREENER_ORDER_OPTIONS: Array<{ value: string; label: string }> = [
  {
    value: "ticker",
    label: "Ticker"
  },
  {
    value: "tickersfilter",
    label: "Tickers Input Filter"
  },
  {
    value: "company",
    label: "Company"
  },
  {
    value: "sector",
    label: "Sector"
  },
  {
    value: "industry",
    label: "Industry"
  },
  {
    value: "country",
    label: "Country"
  },
  {
    value: "index",
    label: "Index"
  },
  {
    value: "exchange",
    label: "Exchange"
  },
  {
    value: "marketcap",
    label: "Market Cap."
  },
  {
    value: "pe",
    label: "Price/Earnings"
  },
  {
    value: "forwardpe",
    label: "Forward Price/Earnings"
  },
  {
    value: "peg",
    label: "PEG (Price/Earnings/Growth)"
  },
  {
    value: "ps",
    label: "Price/Sales"
  },
  {
    value: "pb",
    label: "Price/Book"
  },
  {
    value: "pc",
    label: "Price/Cash"
  },
  {
    value: "pfcf",
    label: "Price/Free Cash Flow"
  },
  {
    value: "dividendyield",
    label: "Dividend Yield"
  },
  {
    value: "payoutratio",
    label: "Payout Ratio"
  },
  {
    value: "eps",
    label: "EPS (TTM)"
  },
  {
    value: "estq1",
    label: "EPS Estimate Next Quarter"
  },
  {
    value: "epsyoy",
    label: "EPS Growth This Year"
  },
  {
    value: "epsyoy1",
    label: "EPS Growth Next Year"
  },
  {
    value: "eps3years",
    label: "EPS Growth Past 3 Years"
  },
  {
    value: "eps5years",
    label: "EPS Growth Past 5 Years"
  },
  {
    value: "estltgrowth",
    label: "EPS Growth Next 5 Years"
  },
  {
    value: "epsqoq",
    label: "EPS Growth Qtr Over Qtr"
  },
  {
    value: "epsyoyttm",
    label: "EPS Year Over Year TTM"
  },
  {
    value: "sales3years",
    label: "Sales Growth Past 3 Years"
  },
  {
    value: "sales5years",
    label: "Sales Growth Past 5 Years"
  },
  {
    value: "salesqoq",
    label: "Sales Growth Qtr Over Qtr"
  },
  {
    value: "salesyoyttm",
    label: "Sales Year Over Year TTM"
  },
  {
    value: "epssurprise",
    label: "EPS Surprise"
  },
  {
    value: "revenuesurprise",
    label: "Revenue Surprise"
  },
  {
    value: "sharesoutstanding2",
    label: "Shares Outstanding"
  },
  {
    value: "sharesfloat",
    label: "Shares Float"
  },
  {
    value: "floatoutstandingpct",
    label: "Float/Outstanding"
  },
  {
    value: "insiderown",
    label: "Insider Ownership"
  },
  {
    value: "insidertrans",
    label: "Insider Transactions"
  },
  {
    value: "instown",
    label: "Institutional Ownership"
  },
  {
    value: "insttrans",
    label: "Institutional Transactions"
  },
  {
    value: "shortinterestshare",
    label: "Short Interest Share"
  },
  {
    value: "shortinterestratio",
    label: "Short Interest Ratio"
  },
  {
    value: "shortinterest",
    label: "Short Interest"
  },
  {
    value: "earningsdate",
    label: "Earnings Date"
  },
  {
    value: "news_date",
    label: "Latest News"
  },
  {
    value: "roa",
    label: "Return on Assets"
  },
  {
    value: "roe",
    label: "Return on Equity"
  },
  {
    value: "roi",
    label: "Return on Invested Capital"
  },
  {
    value: "curratio",
    label: "Current Ratio"
  },
  {
    value: "quickratio",
    label: "Quick Ratio"
  },
  {
    value: "ltdebteq",
    label: "LT Debt/Equity"
  },
  {
    value: "debteq",
    label: "Total Debt/Equity"
  },
  {
    value: "grossmargin",
    label: "Gross Margin"
  },
  {
    value: "opermargin",
    label: "Operating Margin"
  },
  {
    value: "netmargin",
    label: "Net Profit Margin"
  },
  {
    value: "recom",
    label: "Analyst Recommendation"
  },
  {
    value: "perf1w",
    label: "Performance (Week)"
  },
  {
    value: "perf4w",
    label: "Performance (Month)"
  },
  {
    value: "perf13w",
    label: "Performance (Quarter)"
  },
  {
    value: "perf26w",
    label: "Performance (Half Year)"
  },
  {
    value: "perfytd",
    label: "Performance (Year To Date)"
  },
  {
    value: "perf52w",
    label: "Performance (Year)"
  },
  {
    value: "perf3y",
    label: "Performance (3 Years)"
  },
  {
    value: "perf5y",
    label: "Performance (5 Years)"
  },
  {
    value: "perf10y",
    label: "Performance (10 Years)"
  },
  {
    value: "beta",
    label: "Beta"
  },
  {
    value: "averagetruerange",
    label: "Average True Range"
  },
  {
    value: "volatility1w",
    label: "Volatility (Week)"
  },
  {
    value: "volatility4w",
    label: "Volatility (Month)"
  },
  {
    value: "sma20",
    label: "20-Day SMA (Relative)"
  },
  {
    value: "sma50",
    label: "50-Day SMA (Relative)"
  },
  {
    value: "sma200",
    label: "200-Day SMA (Relative)"
  },
  {
    value: "high50d",
    label: "50-Day High (Relative)"
  },
  {
    value: "low50d",
    label: "50-Day Low (Relative)"
  },
  {
    value: "high52w",
    label: "52-Week High (Relative)"
  },
  {
    value: "low52w",
    label: "52-Week Low (Relative)"
  },
  {
    value: "52wrange",
    label: "52-Week Range"
  },
  {
    value: "highat",
    label: "All-Time High (Relative)"
  },
  {
    value: "lowat",
    label: "All-Time Low (Relative)"
  },
  {
    value: "rsi",
    label: "Relative Strength Index (14)"
  },
  {
    value: "averagevolume",
    label: "Average Volume (3 Month)"
  },
  {
    value: "relativevolume",
    label: "Relative Volume"
  },
  {
    value: "change",
    label: "Change"
  },
  {
    value: "changeopen",
    label: "Change from Open"
  },
  {
    value: "gap",
    label: "Gap"
  },
  {
    value: "volume",
    label: "Volume"
  },
  {
    value: "open",
    label: "Open"
  },
  {
    value: "high",
    label: "High"
  },
  {
    value: "low",
    label: "Low"
  },
  {
    value: "price",
    label: "Price"
  },
  {
    value: "prevclose",
    label: "Previous Close"
  },
  {
    value: "targetprice",
    label: "Target Price"
  },
  {
    value: "ipodate",
    label: "IPO Date"
  },
  {
    value: "book",
    label: "Book Value per Share"
  },
  {
    value: "cashpershare",
    label: "Cash per Share"
  },
  {
    value: "dividend",
    label: "Dividend"
  },
  {
    value: "dividendexdate",
    label: "Dividend Ex-Date"
  },
  {
    value: "dividendttm",
    label: "Dividend TTM"
  },
  {
    value: "dividend1y",
    label: "Dividend Growth (1 Year)"
  },
  {
    value: "dividend3y",
    label: "Dividend Growth (3 Year)"
  },
  {
    value: "dividend5y",
    label: "Dividend Growth (5 Year)"
  },
  {
    value: "employees",
    label: "Employees"
  },
  {
    value: "income",
    label: "Income"
  },
  {
    value: "sales",
    label: "Sales"
  },
  {
    value: "enterpriseValue",
    label: "Enterprise Value"
  },
  {
    value: "evebitda",
    label: "EV/EBITDA"
  },
  {
    value: "evsales",
    label: "EV/Sales"
  },
  {
    value: "optionable",
    label: "Optionable"
  },
  {
    value: "shortable",
    label: "Shortable"
  },
  {
    value: "newsurl",
    label: "News URL"
  },
  {
    value: "newstitle",
    label: "News Title"
  },
  {
    value: "newstime",
    label: "News Time"
  },
  {
    value: "e.category",
    label: "ETF - Single Category"
  },
  {
    value: "e.tags",
    label: "ETF - Tags"
  },
  {
    value: "e.totalholdings",
    label: "ETF - Total Holdings"
  },
  {
    value: "e.assetsundermanagement",
    label: "ETF - Assets Under Management"
  },
  {
    value: "e.netflows1month",
    label: "ETF - Net Fund Flows (1 Month)"
  },
  {
    value: "e.netflows1monthpct",
    label: "ETF - Net Fund Flows% (1 Month)"
  },
  {
    value: "e.netflows3month",
    label: "ETF - Net Fund Flows (3 Month)"
  },
  {
    value: "e.netflows3monthpct",
    label: "ETF - Net Fund Flows% (3 Month)"
  },
  {
    value: "e.netflowsytd",
    label: "ETF - Net Fund Flows (YTD)"
  },
  {
    value: "e.netflowsytdpct",
    label: "ETF - Net Fund Flows% (YTD)"
  },
  {
    value: "e.return1year",
    label: "ETF - Annualized Return (1 Year)"
  },
  {
    value: "e.return3year",
    label: "ETF - Annualized Return (3 Year)"
  },
  {
    value: "e.return5year",
    label: "ETF - Annualized Return (5 Year)"
  },
  {
    value: "e.netexpenseratio",
    label: "ETF - Net Expense Ratio"
  },
  {
    value: "e.activepassive",
    label: "ETF - Active Passive"
  },
  {
    value: "e.assettype",
    label: "ETF - Asset Type"
  },
  {
    value: "e.etftype",
    label: "ETF - Type"
  },
  {
    value: "e.sectortheme",
    label: "ETF - Sector/Theme"
  }
];

export const SCREENER_SIGNAL_OPTIONS: Array<{ value: string; label: string }> = [
  {
    value: "",
    label: "None (all stocks)"
  },
  {
    value: "ta_topgainers",
    label: "Top Gainers"
  },
  {
    value: "ta_toplosers",
    label: "Top Losers"
  },
  {
    value: "ta_newhigh",
    label: "New High"
  },
  {
    value: "ta_newlow",
    label: "New Low"
  },
  {
    value: "ta_mostvolatile",
    label: "Most Volatile"
  },
  {
    value: "ta_mostactive",
    label: "Most Active"
  },
  {
    value: "ta_unusualvolume",
    label: "Unusual Volume"
  },
  {
    value: "ta_overbought",
    label: "Overbought"
  },
  {
    value: "ta_oversold",
    label: "Oversold"
  },
  {
    value: "n_downgrades",
    label: "Downgrades"
  },
  {
    value: "n_upgrades",
    label: "Upgrades"
  },
  {
    value: "n_earningsbefore",
    label: "Earnings Before"
  },
  {
    value: "n_earningsafter",
    label: "Earnings After"
  },
  {
    value: "it_latestbuys",
    label: "Recent Insider Buying"
  },
  {
    value: "it_latestsales",
    label: "Recent Insider Selling"
  },
  {
    value: "n_majornews",
    label: "Major News"
  },
  {
    value: "ta_p_horizontal",
    label: "Horizontal S/R"
  },
  {
    value: "ta_p_tlresistance",
    label: "TL Resistance"
  },
  {
    value: "ta_p_tlsupport",
    label: "TL Support"
  },
  {
    value: "ta_p_wedgeup",
    label: "Wedge Up"
  },
  {
    value: "ta_p_wedgedown",
    label: "Wedge Down"
  },
  {
    value: "ta_p_wedgeresistance",
    label: "Triangle Ascending"
  },
  {
    value: "ta_p_wedgesupport",
    label: "Triangle Descending"
  },
  {
    value: "ta_p_wedge",
    label: "Wedge"
  },
  {
    value: "ta_p_channelup",
    label: "Channel Up"
  },
  {
    value: "ta_p_channeldown",
    label: "Channel Down"
  },
  {
    value: "ta_p_channel",
    label: "Channel"
  },
  {
    value: "ta_p_doubletop",
    label: "Double Top"
  },
  {
    value: "ta_p_doublebottom",
    label: "Double Bottom"
  },
  {
    value: "ta_p_multipletop",
    label: "Multiple Top"
  },
  {
    value: "ta_p_multiplebottom",
    label: "Multiple Bottom"
  },
  {
    value: "ta_p_headandshoulders",
    label: "Head & Shoulders"
  },
  {
    value: "ta_p_headandshouldersinv",
    label: "Head & Shoulders Inverse"
  }
];

export const SCREENER_FILTER_KEYS: string[] = [
  "ah_change",
  "ah_close",
  "analystRecom",
  "avgVolume",
  "country",
  "currentVolume",
  "dividendYield",
  "earningsDate",
  "etf_active",
  "etf_assettype",
  "etf_bondmaturity",
  "etf_bondtype",
  "etf_category",
  "etf_commoditytype",
  "etf_currency",
  "etf_developed",
  "etf_dividendtype",
  "etf_esgtype",
  "etf_etftype",
  "etf_fundflows",
  "etf_growthvalue",
  "etf_indexweight",
  "etf_inverse",
  "etf_mktcap",
  "etf_nav",
  "etf_netexpense",
  "etf_quanttype",
  "etf_region",
  "etf_return",
  "etf_sectortheme",
  "etf_sponsor",
  "etf_structuretype",
  "etf_tags",
  "exchange",
  "fa_curratio",
  "fa_debteq",
  "fa_divgrowth",
  "fa_eps3years",
  "fa_eps5years",
  "fa_epsqoq",
  "fa_epsrev",
  "fa_epsyoy",
  "fa_epsyoy1",
  "fa_epsyoyttm",
  "fa_estltgrowth",
  "fa_evebitda",
  "fa_evsales",
  "fa_fpe",
  "fa_grossmargin",
  "fa_ltdebteq",
  "fa_netmargin",
  "fa_opermargin",
  "fa_payoutratio",
  "fa_pb",
  "fa_pc",
  "fa_pe",
  "fa_peg",
  "fa_pfcf",
  "fa_ps",
  "fa_quickratio",
  "fa_roa",
  "fa_roe",
  "fa_roi",
  "fa_sales3years",
  "fa_sales5years",
  "fa_salesqoq",
  "fa_salesyoyttm",
  "float",
  "index",
  "industry",
  "ipoDate",
  "marketCap",
  "news_date",
  "optionShort",
  "priceBand",
  "relVolume",
  "sector",
  "sh_insiderown",
  "sh_insidertrans",
  "sh_instown",
  "sh_insttrans",
  "sharesOutstanding",
  "shortFloat",
  "subTheme",
  "ta_alltime",
  "ta_averagetruerange",
  "ta_beta",
  "ta_candlestick",
  "ta_change",
  "ta_changeopen",
  "ta_gap",
  "ta_highlow20d",
  "ta_highlow50d",
  "ta_highlow52w",
  "ta_pattern",
  "ta_perf",
  "ta_perf2",
  "ta_rsi",
  "ta_sma20",
  "ta_sma200",
  "ta_sma50",
  "ta_volatility",
  "targetPrice",
  "theme",
  "trades"
];
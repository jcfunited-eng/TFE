import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";

export const UI_PAGE_KEYS = [
  "home",
  "help",
  "support",
  "signIn",
  "account",
  "recommendations",
  "watchlist",
  "portfolioAdvisor",
  "legal",
  "adminConsole",
] as const;

export type UiPageKey = (typeof UI_PAGE_KEYS)[number];

export type UiBackgroundImages = Record<UiPageKey, string>;

export type UiConfig = {
  backgroundImages: UiBackgroundImages;
};

const DEFAULT_IMAGE = "/landing-zen.jpg";

const DEFAULT_CONFIG: UiConfig = {
  backgroundImages: {
    home: DEFAULT_IMAGE,
    help: DEFAULT_IMAGE,
    support: DEFAULT_IMAGE,
    signIn: DEFAULT_IMAGE,
    account: DEFAULT_IMAGE,
    recommendations: DEFAULT_IMAGE,
    watchlist: DEFAULT_IMAGE,
    portfolioAdvisor: DEFAULT_IMAGE,
    legal: DEFAULT_IMAGE,
    adminConsole: DEFAULT_IMAGE,
  },
};

const CONFIG_PATH = path.join(process.cwd(), "data", "ui-config.json");

function sanitizeImagePath(value: unknown): string {
  if (typeof value !== "string") {
    return DEFAULT_IMAGE;
  }

  const trimmed = value.trim();
  const valid = /^\/[a-zA-Z0-9_\-./]+\.(jpg|jpeg|png|webp)$/i.test(trimmed);
  if (!valid) {
    return DEFAULT_IMAGE;
  }

  return trimmed;
}

function sanitizeBackgroundImages(raw: unknown): UiBackgroundImages {
  const source = typeof raw === "object" && raw !== null ? (raw as Partial<Record<UiPageKey, unknown>>) : {};

  return {
    home: sanitizeImagePath(source.home),
    help: sanitizeImagePath(source.help),
    support: sanitizeImagePath(source.support),
    signIn: sanitizeImagePath(source.signIn),
    account: sanitizeImagePath(source.account),
    recommendations: sanitizeImagePath(source.recommendations),
    watchlist: sanitizeImagePath(source.watchlist),
    portfolioAdvisor: sanitizeImagePath(source.portfolioAdvisor),
    legal: sanitizeImagePath(source.legal),
    adminConsole: sanitizeImagePath(source.adminConsole),
  };
}

export function pageKeyFromRoute(route: string): UiPageKey {
  if (route === "/") return "home";
  if (route === "/help") return "help";
  if (route === "/support") return "support";
  if (route === "/sign-in") return "signIn";
  if (route === "/account") return "account";
  if (route === "/recommendations") return "recommendations";
  if (route === "/watchlist") return "watchlist";
  if (route === "/portfolio-advisor") return "portfolioAdvisor";
  if (route === "/legal") return "legal";
  if (route === "/admin-console") return "adminConsole";
  return "home";
}

export async function getUiConfig(): Promise<UiConfig> {
  try {
    const raw = await readFile(CONFIG_PATH, "utf8");
    const parsed = JSON.parse(raw) as {
      backgroundImages?: unknown;
      homeBackgroundImage?: unknown;
    };

    if (parsed.backgroundImages) {
      return { backgroundImages: sanitizeBackgroundImages(parsed.backgroundImages) };
    }

    // Backward compatibility for previous single-value shape.
    if (parsed.homeBackgroundImage) {
      const homeValue = sanitizeImagePath(parsed.homeBackgroundImage);
      return {
        backgroundImages: {
          ...DEFAULT_CONFIG.backgroundImages,
          home: homeValue,
        },
      };
    }

    return DEFAULT_CONFIG;
  } catch {
    return DEFAULT_CONFIG;
  }
}

export async function setUiConfig(next: Partial<UiBackgroundImages>): Promise<UiConfig> {
  const current = await getUiConfig();

  const merged: UiConfig = {
    backgroundImages: {
      home: sanitizeImagePath(next.home ?? current.backgroundImages.home),
      help: sanitizeImagePath(next.help ?? current.backgroundImages.help),
      support: sanitizeImagePath(next.support ?? current.backgroundImages.support),
      signIn: sanitizeImagePath(next.signIn ?? current.backgroundImages.signIn),
      account: sanitizeImagePath(next.account ?? current.backgroundImages.account),
      recommendations: sanitizeImagePath(next.recommendations ?? current.backgroundImages.recommendations),
      watchlist: sanitizeImagePath(next.watchlist ?? current.backgroundImages.watchlist),
      portfolioAdvisor: sanitizeImagePath(next.portfolioAdvisor ?? current.backgroundImages.portfolioAdvisor),
      legal: sanitizeImagePath(next.legal ?? current.backgroundImages.legal),
      adminConsole: sanitizeImagePath(next.adminConsole ?? current.backgroundImages.adminConsole),
    },
  };

  await mkdir(path.dirname(CONFIG_PATH), { recursive: true });
  await writeFile(CONFIG_PATH, `${JSON.stringify(merged, null, 2)}\n`, "utf8");

  return merged;
}

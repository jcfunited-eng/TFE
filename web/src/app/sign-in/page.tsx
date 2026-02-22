import SiteFrame from "@/components/SiteFrame";
import { sanitizeNextPath } from "@/lib/auth-session";
import { getCurrentServerUser } from "@/lib/server-auth";
import { getUiConfig } from "@/lib/ui-config";
import { redirect } from "next/navigation";

type RawSearchParams = Record<string, string | string[] | undefined>;

type SignInPageProps = {
  searchParams?: RawSearchParams | Promise<RawSearchParams>;
};

function pickFirst(value: string | string[] | undefined): string {
  if (Array.isArray(value)) return value[0] ?? "";
  return value ?? "";
}

function errorMessageFromCode(errorCode: string): string {
  if (errorCode === "missing_credentials") return "Enter both username and password.";
  if (errorCode === "invalid_credentials") return "Sign in failed. Check username/password or account access.";
  if (errorCode === "mfa_required") return "MFA code is required for this account.";
  if (errorCode === "invalid_mfa") return "Invalid MFA code.";
  return "";
}

export default async function SignInPage(props: SignInPageProps) {
  const config = await getUiConfig();
  const params = (await props.searchParams) ?? {};

  const nextPath = sanitizeNextPath(pickFirst(params.next));
  const errorCode = pickFirst(params.error);
  const errorMessage = errorMessageFromCode(errorCode);

  const existingUser = await getCurrentServerUser();
  if (existingUser) {
    redirect(nextPath);
  }

  return (
    <SiteFrame pageBackgroundImage={config.backgroundImages.signIn}>
      <section className="surface-card" style={{ maxWidth: 560 }}>
        <h1>Sign In</h1>
        <p>Sign in to access your account, recommendations, watchlist, and portfolio.</p>

        <form method="post" action="/api/auth/sign-in" className="section-stack" style={{ marginTop: 12 }}>
          <input type="hidden" name="next" value={nextPath} />

          <label htmlFor="signin-username">Username</label>
          <input id="signin-username" name="username" className="tfe-input" type="text" placeholder="username" autoComplete="username" required />

          <label htmlFor="signin-password">Password</label>
          <input
            id="signin-password"
            name="password"
            className="tfe-input"
            type="password"
            placeholder="Enter your password"
            autoComplete="current-password"
            required
          />

          <label htmlFor="signin-mfa">MFA Code (if required)</label>
          <input
            id="signin-mfa"
            name="mfaCode"
            className="tfe-input"
            type="text"
            inputMode="numeric"
            pattern="[0-9]{6}"
            placeholder="6-digit code"
            autoComplete="one-time-code"
          />

          <button className="btn btn-primary" type="submit" style={{ maxWidth: 180 }}>
            Sign In
          </button>
        </form>

        {errorMessage ? <p className="tfe-error" style={{ marginTop: 10 }}>{errorMessage}</p> : null}
      </section>
    </SiteFrame>
  );
}

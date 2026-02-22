import SiteFrame from "@/components/SiteFrame";
import { isUserAccessExpired } from "@/lib/user-store";
import { requireServerUser } from "@/lib/server-auth";
import { getUiConfig } from "@/lib/ui-config";

type RawSearchParams = Record<string, string | string[] | undefined>;

type AccountPageProps = {
  searchParams?: RawSearchParams | Promise<RawSearchParams>;
};

function pickFirst(value: string | string[] | undefined): string {
  if (Array.isArray(value)) return value[0] ?? "";
  return value ?? "";
}

export default async function AccountPage(props: AccountPageProps) {
  const user = await requireServerUser("/account");
  const config = await getUiConfig();

  const params = (await props.searchParams) ?? {};
  const errorCode = pickFirst(params.error);
  const adminError = errorCode === "admin_required" ? "Admin role is required for that page." : "";

  return (
    <SiteFrame pageBackgroundImage={config.backgroundImages.account}>
      <section className="surface-card" style={{ maxWidth: 780 }}>
        <h1>Account</h1>
        <p>Signed in user profile and access details.</p>

        {adminError ? <p className="tfe-error">{adminError}</p> : null}

        <h2>Profile</h2>
        <ul>
          <li>Username: {user.username}</li>
          <li>Role: {user.role}</li>
          <li>Test user: {user.is_test_user ? "Yes" : "No"}</li>
          <li>Created at: {new Date(user.created_at).toLocaleString()}</li>
        </ul>

        <h2>Access</h2>
        <ul>
          <li>Account active: {user.is_active ? "Yes" : "No"}</li>
          <li>Access expiration: {user.access_expires_at ? new Date(user.access_expires_at).toLocaleString() : "No expiry"}</li>
          <li>Expired now: {isUserAccessExpired(user.access_expires_at) ? "Yes" : "No"}</li>
        </ul>

        <h2>Session</h2>
        <form method="post" action="/api/auth/sign-out" className="section-stack" style={{ maxWidth: 220 }}>
          <input type="hidden" name="next" value="/sign-in" />
          <button className="btn btn-ghost" type="submit">
            Sign Out
          </button>
        </form>
      </section>
    </SiteFrame>
  );
}

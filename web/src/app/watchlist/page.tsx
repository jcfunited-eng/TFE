import SiteFrame from "@/components/SiteFrame";
import WatchlistManager from "@/components/WatchlistManager";
import { requireServerUser } from "@/lib/server-auth";
import { getUiConfig } from "@/lib/ui-config";

export default async function WatchlistPage() {
  await requireServerUser("/watchlist");
  const config = await getUiConfig();

  return (
    <SiteFrame pageBackgroundImage={config.backgroundImages.watchlist}>
      <section className="surface-card">
        <h1>Watchlist</h1>
        <WatchlistManager />
      </section>
    </SiteFrame>
  );
}

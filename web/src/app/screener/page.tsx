import SiteFrame from "@/components/SiteFrame";
import ScreenerWorkbench from "@/components/ScreenerWorkbench";
import { requireServerUser } from "@/lib/server-auth";
import { getUiConfig } from "@/lib/ui-config";

export default async function ScreenerPage() {
  await requireServerUser("/screener");
  const config = await getUiConfig();

  return (
    <SiteFrame pageBackgroundImage={config.backgroundImages.screener}>
      <section className="surface-card">
        <h1>Screener</h1>
        <ScreenerWorkbench />
      </section>
    </SiteFrame>
  );
}

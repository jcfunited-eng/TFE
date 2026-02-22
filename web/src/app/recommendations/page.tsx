import SiteFrame from "@/components/SiteFrame";
import RecommendationsQuickCheck from "@/components/RecommendationsQuickCheck";
import { requireServerUser } from "@/lib/server-auth";
import { getUiConfig } from "@/lib/ui-config";

export default async function RecommendationsPage() {
  await requireServerUser("/recommendations");
  const config = await getUiConfig();

  return (
    <SiteFrame pageBackgroundImage={config.backgroundImages.recommendations}>
      <section className="surface-card">
        <h1>Recommendations</h1>
        <RecommendationsQuickCheck />
      </section>
    </SiteFrame>
  );
}

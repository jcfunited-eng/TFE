import HomeScrollStory from "@/components/HomeScrollStory";
import SiteFrame from "@/components/SiteFrame";
import { getUiConfig } from "@/lib/ui-config";

export default async function HomePage() {
  const config = await getUiConfig();

  return (
    <SiteFrame pageBackgroundImage={config.backgroundImages.home} hideHeader>
      <HomeScrollStory backgroundImage={config.backgroundImages.home} />
    </SiteFrame>
  );
}

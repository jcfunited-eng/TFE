import { notFound } from "next/navigation";
import ChannelBookPage from "@/components/ChannelBookPage";
import SiteFrame from "@/components/SiteFrame";
import {
  getChannelBookView,
  getChannelPerceptionView,
  type ChannelBookView,
  type ChannelCode,
} from "@/lib/channel-books";
import { requireServerAdminUser } from "@/lib/server-auth";
import { getUiConfig } from "@/lib/ui-config";
import styles from "./page.module.css";


export const dynamic = "force-dynamic";

const CHANNELS: Record<string, ChannelCode> = { ch3: "CH3", ch4: "CH4", ch6: "CH6" };


async function receiveBook(channel: ChannelCode): Promise<{
  book: ChannelBookView | null;
  failure: string | null;
}> {
  try {
    return { book: await getChannelBookView(channel), failure: null };
  } catch (error) {
    return {
      book: null,
      failure: error instanceof Error ? error.message : String(error),
    };
  }
}


export default async function ChannelPage({ params }: { params: Promise<{ channel: string }> }) {
  const { channel: slug } = await params;
  const channel = CHANNELS[slug.toLowerCase()];
  if (!channel) notFound();

  await requireServerAdminUser(`/portfolio/${slug}`);
  const [config, received, perception] = await Promise.all([
    getUiConfig(),
    receiveBook(channel),
    channel === "CH6" ? getChannelPerceptionView() : Promise.resolve(null),
  ]);

  if (received.book) {
    return (
      <SiteFrame pageBackgroundImage={config.backgroundImages.portfolioAdvisor}>
        <ChannelBookPage book={received.book} perception={perception} />
      </SiteFrame>
    );
  }

  return (
    <SiteFrame pageBackgroundImage={config.backgroundImages.portfolioAdvisor}>
      <section className={`surface-card ${styles.channelPage}`}>
        <h1>{channel} book unavailable</h1>
        <p className={styles.failure}>{received.failure}</p>
        <p>No fallback values were inserted. The page will remain unavailable until a received book passes its SHA-256 receipt.</p>
      </section>
    </SiteFrame>
  );
}

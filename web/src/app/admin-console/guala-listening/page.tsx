import GualaOperatorListeningClient from "@/components/GualaOperatorListeningClient";
import { requireServerClerkAdminUser } from "@/lib/server-auth";

export const dynamic = "force-dynamic";

export default async function GualaOperatorListeningPage() {
  await requireServerClerkAdminUser("/admin-console/guala-listening");
  return <GualaOperatorListeningClient />;
}

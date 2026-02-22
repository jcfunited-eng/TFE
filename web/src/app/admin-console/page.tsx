import AdminConsoleClient from "@/components/AdminConsoleClient";
import { requireServerAdminUser } from "@/lib/server-auth";

export default async function AdminConsolePage() {
  await requireServerAdminUser("/admin-console");
  return <AdminConsoleClient />;
}

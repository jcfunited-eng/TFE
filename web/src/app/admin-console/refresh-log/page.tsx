import AdminRefreshLogsClient from "@/components/AdminRefreshLogsClient";
import { requireServerAdminUser } from "@/lib/server-auth";

export default async function AdminRefreshLogPage() {
  await requireServerAdminUser("/admin-console/refresh-log");
  return <AdminRefreshLogsClient />;
}

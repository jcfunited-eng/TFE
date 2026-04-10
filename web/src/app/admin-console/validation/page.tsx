import { requireServerAdminUser } from "@/lib/server-auth";
import ValidationDashboard from "@/components/ValidationDashboard";

export const dynamic = "force-dynamic";

export default async function ValidationPage() {
  await requireServerAdminUser("/admin-console/validation");
  return (
    <main className="min-h-screen bg-gray-950 text-gray-200 p-6">
      <div className="max-w-screen-2xl mx-auto">
        <div className="mb-6">
          <h1 className="text-xl font-semibold text-white">DSF-AI Validation Dashboard</h1>
          <p className="text-gray-500 text-xs mt-1">
            Physics performance, portfolio metrics, mathematical expectancy, and infrastructure health.
            Validation period started April 6, 2026.
          </p>
        </div>
        <ValidationDashboard />
      </div>
    </main>
  );
}

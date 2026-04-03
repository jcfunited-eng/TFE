import { redirect } from "next/navigation";
import { readSessionUserFromRequest } from "@/lib/auth-session";
import { headers } from "next/headers";
import AuditorReport from "@/components/AuditorReport";

export const dynamic = "force-dynamic";

export default async function AuditorPage() {
  // Server-side admin guard
  const h = await headers();
  // Build a minimal Request-like object for the auth helper
  const req = new Request("http://localhost", { headers: h });
  const user = await readSessionUserFromRequest(req as never).catch(() => null);
  if (!user || user.role !== "admin") {
    redirect("/");
  }

  return (
    <main className="min-h-screen bg-gray-950 text-gray-200 p-6">
      <div className="max-w-screen-2xl mx-auto">
        <div className="mb-6">
          <h1 className="text-xl font-semibold text-white">Trade Audit Console</h1>
          <p className="text-gray-500 text-xs mt-1">
            Signal provenance · Execution trace · Stealth queue · Circuit breaker log
          </p>
        </div>
        <AuditorReport />
      </div>
    </main>
  );
}

import { UserProfile } from "@clerk/nextjs";

export default function AccountPage() {
  return (
    <main
      style={{
        display: "flex",
        minHeight: "100vh",
        alignItems: "flex-start",
        justifyContent: "center",
        paddingTop: "2rem",
        paddingBottom: "2rem",
      }}
    >
      <UserProfile />
    </main>
  );
}

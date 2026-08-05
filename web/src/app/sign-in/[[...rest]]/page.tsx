import { SignIn } from "@clerk/nextjs";

export default function SignInCatchAllPage() {
  return (
    <main
      style={{
        display: "flex",
        minHeight: "100vh",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <SignIn />
    </main>
  );
}

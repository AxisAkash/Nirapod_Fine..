import type { Metadata } from "next";
import { Suspense } from "react";
import { SignIn } from "@clerk/nextjs";

import { Skeleton } from "@/components/ui/skeleton";

export const metadata: Metadata = { title: "Sign in" };

export default function SignInPage() {
  // Clerk's form reads the current URL on the client, so it streams in behind a placeholder.
  return (
    <Suspense fallback={<Skeleton className="h-96 w-full max-w-[25rem]" />}>
      <SignIn />
    </Suspense>
  );
}

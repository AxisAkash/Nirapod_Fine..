import type { Metadata } from "next";
import { Suspense } from "react";
import { SignUp } from "@clerk/nextjs";

import { Skeleton } from "@/components/ui/skeleton";

export const metadata: Metadata = { title: "Create account" };

export default function SignUpPage() {
  return (
    <Suspense fallback={<Skeleton className="h-[28rem] w-full max-w-[25rem]" />}>
      <SignUp />
    </Suspense>
  );
}

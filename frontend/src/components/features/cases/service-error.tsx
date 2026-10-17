"use client";

import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";

export function ServiceError({ message }: { message: string }) {
  const router = useRouter();
  return (
    <div role="alert" className="mx-auto max-w-lg rounded-xl border bg-card p-6 text-center">
      <h2 className="text-lg font-semibold">We could not load this page</h2>
      <p className="mt-2 text-sm text-muted-foreground">{message}</p>
      <Button className="mt-4" onClick={() => router.refresh()}>
        Try again
      </Button>
    </div>
  );
}

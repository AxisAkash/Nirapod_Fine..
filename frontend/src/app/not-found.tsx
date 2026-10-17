import Link from "next/link";

import { buttonVariants } from "@/components/ui/button";

export default function NotFound() {
  return (
    <main className="flex flex-1 flex-col items-center justify-center gap-4 px-4 py-24 text-center">
      <p className="font-mono text-sm text-muted-foreground">404</p>
      <h1 className="text-3xl font-semibold">We could not find that page</h1>
      <p className="max-w-md text-muted-foreground">The page may have moved, or the case belongs to another account.</p>
      <Link href="/dashboard" className={buttonVariants({ size: "lg" })}>
        Go to the dashboard
      </Link>
    </main>
  );
}

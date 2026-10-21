import { Skeleton } from "@/components/ui/skeleton";

/** Placeholder shown while a page's data streams in. */
export function PageSkeleton() {
  return (
    <div aria-busy="true" aria-label="Loading" className="grid gap-4">
      <Skeleton className="h-10 w-64" />
      <Skeleton className="h-40" />
      <Skeleton className="h-72" />
    </div>
  );
}

export function StatsSkeleton() {
  return (
    <div aria-busy="true" aria-label="Loading your checks" className="grid gap-2.5 sm:grid-cols-3">
      {Array.from({ length: 3 }).map((_, i) => (
        <Skeleton key={i} className="h-[4.5rem]" />
      ))}
    </div>
  );
}

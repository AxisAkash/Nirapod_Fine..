"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";

import { NativeSelect } from "@/components/ui/native-select";
import { RESULT_GROUPS, type ResultGroup } from "@/constants/status";

export function ResultFilter() {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const current = params.get("result") ?? "all";
  return (
    <label className="flex items-center gap-2 text-[0.78rem] font-medium text-muted-foreground">
      Result
      <NativeSelect className="w-56" value={current} onChange={(e) => router.push(e.target.value === "all" ? pathname : `${pathname}?result=${e.target.value}`)}>
        <option value="all">All results</option>
        {(Object.keys(RESULT_GROUPS) as ResultGroup[]).map((k) => (
          <option key={k} value={k}>
            {RESULT_GROUPS[k].label}
          </option>
        ))}
      </NativeSelect>
    </label>
  );
}

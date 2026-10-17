import Link from "next/link";

import { SITE } from "@/config/site";

export function Logo({ href = "/" }: { href?: string }) {
  return (
    <Link href={href} className="font-heading text-[1.1rem] font-semibold text-primary">
      {SITE.name}
    </Link>
  );
}

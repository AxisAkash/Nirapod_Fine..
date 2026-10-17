import Link from "next/link";

import { amberButton, outlineWhiteButton, sizeLg } from "@/components/features/landing/buttons";
import { SampleReport } from "@/components/features/landing/sample-report";
import { HERO_CAPS } from "@/constants/landing";
import { cn } from "@/lib/utils";

export function Hero() {
  return (
    <section className="bg-navy py-[clamp(40px,6vw,88px)] text-[#eaf0fb]">
      <div className="mx-auto grid max-w-[1320px] items-center gap-[clamp(32px,5vw,72px)] px-[clamp(16px,3vw,32px)] lg:grid-cols-[minmax(0,1fr)_minmax(0,540px)]">
        <div className="min-w-0">
          <h1 className="mb-5 font-sans text-[clamp(2.2rem,4.4vw,3.5rem)] leading-[1.08] font-semibold tracking-[-0.02em] text-white">
            Was your traffic fine <span className="font-heading font-medium tracking-[-0.01em] text-lamp">charged correctly?</span>
          </h1>
          <p className="mb-7 max-w-[52ch] text-[1.1rem] text-[#b9c8e2]">
            Upload your mamla receipt to check the offence, review the applicable legal limit, and understand the rules behind the result.
          </p>
          <div className="flex flex-wrap gap-2">
            <Link href="/upload" className={cn(amberButton, sizeLg)}>
              Check Mamla
            </Link>
            <a href="#how" className={cn(outlineWhiteButton, sizeLg)}>
              See How It Works
            </a>
          </div>
          <ul className="mt-7 flex flex-wrap gap-2">
            {HERO_CAPS.map((c) => (
              <li key={c} className="flex items-center gap-2 rounded-md border border-white/20 px-[11px] py-[5px] text-[0.82rem] text-[#d3def1] before:size-1.5 before:rounded-full before:bg-lamp before:content-['']">
                {c}
              </li>
            ))}
          </ul>
        </div>
        <div className="min-w-0 max-w-[560px] lg:max-w-none">
          <SampleReport />
        </div>
      </div>
    </section>
  );
}

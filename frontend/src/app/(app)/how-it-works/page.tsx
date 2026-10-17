import type { Metadata } from "next";
import Link from "next/link";

import { PageHeader } from "@/components/layouts/page-header";

export const metadata: Metadata = { title: "How it works" };

const STEPS = [
  { no: "01", title: "Provide a notice", text: "Paste the URL of a traffic fine notice, or upload a receipt. This prototype cannot read external URLs, so it offers an illustrative sample notice instead." },
  { no: "02", title: "Rules are checked", text: "The offence is matched to a section, the amount is compared with the configured limit, and repeat-offence and exception rules are evaluated." },
  { no: "03", title: "Review the result", text: "The result lists the evidence, the legal references and anything missing. It is informational, not an authoritative legal determination." },
];

export default function HowItWorksPage() {
  return (
    <>
      <PageHeader eyebrow="Guide" title="How Nirapod Fine works" />
      <ol className="m-0 grid list-none gap-6 p-0 md:grid-cols-3 md:gap-8">
        {STEPS.map((s) => (
          <li key={s.no} className="min-w-0 border-l-2 pl-5 md:border-l-0 md:pl-0">
            <span className="block font-mono text-[0.8rem] font-medium text-primary">{s.no}</span>
            <div className="relative my-2.5 mb-4 hidden h-px bg-border before:absolute before:-top-1 before:left-0 before:size-[9px] before:rounded-full before:bg-primary before:content-[''] md:block" />
            <h3 className="mb-1.5 font-sans text-[1.1rem] leading-[1.3] font-semibold">{s.title}</h3>
            <p className="max-w-[38ch] text-[0.94rem] text-muted-foreground">{s.text}</p>
          </li>
        ))}
      </ol>
      <div className="rounded-r-md border-l-[3px] border-primary bg-accent px-3.5 py-2.5 text-[0.88rem]">
        <b>Limitations.</b> Fine limits and exception rules come from the prototype&apos;s configured dataset, built from published summary guides. They have not been verified against the official Road Transport Act, 2018.
      </div>
      <div>
        <Link href="/dashboard#notice" className="inline-flex items-center rounded-md border border-lamp bg-lamp px-4 py-2 text-sm font-semibold text-[#1a1305] hover:brightness-105">
          Analyze a notice
        </Link>
      </div>
    </>
  );
}

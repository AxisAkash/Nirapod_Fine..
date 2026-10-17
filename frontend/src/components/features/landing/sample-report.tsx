import { LandingIcon } from "@/components/features/landing/landing-icon";

/** An illustrative verification report shown in the hero. It is labelled as a sample, not a real case. */
export function SampleReport() {
  return (
    <figure aria-label="Sample verification report, illustrative only" className="m-0 overflow-hidden rounded-[10px] border bg-card text-foreground shadow-[0_14px_34px_rgba(0,0,0,0.3)]">
      <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-2 border-b bg-muted px-4 py-3">
        <b className="font-mono text-[0.72rem] font-medium tracking-[0.07em] text-muted-foreground uppercase">Verification report</b>
        <span className="rounded-full bg-muted px-[9px] py-0.5 font-mono text-[0.72rem] text-muted-foreground">SAMPLE · ILLUSTRATIVE</span>
      </div>
      <div className="grid gap-3.5 p-4">
        <p className="text-[0.8rem] text-muted-foreground">Illustrative case for demonstration. Not a real receipt and not a legal conclusion.</p>
        <div className="flex items-start gap-3 rounded-lg border border-warn bg-warn-bg px-3.5 py-3">
          <LandingIcon name="alert" className="mt-0.5 size-5 shrink-0 text-warn" />
          <div>
            <strong className="block text-base">Review required</strong>
            <span className="text-[0.86rem] text-muted-foreground">The charged amount is above the reference limit.</span>
          </div>
        </div>
        <div className="grid gap-2.5 sm:grid-cols-2">
          <Field wide label="Offence" value="Exceeding the speed limit" />
          <Field label="Section" value="Section 87" />
          <Field label="Amount charged" value="৳15,000" />
          <Field label="Reference limit" value="৳10,000" />
          <Field label="Difference" value="৳5,000 above" />
        </div>
        <div>
          <small className="mb-1 block font-mono text-[0.66rem] font-medium tracking-[0.06em] text-muted-foreground uppercase">Why this was flagged</small>
          <p className="text-[0.88rem]">
            The charged amount is higher than the limit configured for this section in the prototype. A person should check the receipt details and the official Act.
          </p>
        </div>
        <div className="rounded-r-md border-l-[3px] border-primary bg-accent px-3 py-2.5 text-[0.84rem]">
          <b className="font-semibold">Legal reference</b>
          <br />
          Road Transport Act, 2018, Section 87. Summary taken from the prototype dataset, not an authoritative text.
        </div>
      </div>
      <div className="flex items-center gap-2 border-t px-4 py-2.5 font-mono text-[0.74rem] text-muted-foreground">
        <i className="size-2 shrink-0 rounded-full bg-ok" />
        Audit trail: dataset version and result hash recorded
      </div>
    </figure>
  );
}

function Field({ label, value, wide }: { label: string; value: string; wide?: boolean }) {
  return (
    <div className={`min-w-0 rounded-md border px-2.5 py-2 ${wide ? "sm:col-span-2" : ""}`}>
      <small className="mb-0.5 block font-mono text-[0.66rem] font-medium tracking-[0.06em] text-muted-foreground uppercase">{label}</small>
      <b className="text-[0.98rem] font-semibold tabular-nums">{value}</b>
    </div>
  );
}

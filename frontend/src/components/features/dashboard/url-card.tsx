"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";

import { amberButton, sizeLg } from "@/components/features/landing/buttons";
import { ReceiptPaper } from "@/components/features/cases/receipt-paper";
import { ProcessingSteps } from "@/components/features/upload/processing-steps";
import { Input } from "@/components/ui/input";
import { NativeSelect } from "@/components/ui/native-select";
import { useAnalysisFlow } from "@/hooks/use-analysis-flow";
import { capitalize, shortUrl } from "@/lib/cases";
import { formatNumber } from "@/lib/format";
import { checkNoticeUrl } from "@/lib/validation";
import { cn } from "@/lib/utils";
import { analyzeSample, getScenarios } from "@/services/cases.client";
import type { DummyScenario } from "@/types/api";

type PanelState = "idle" | "checking" | "unsupported" | "example";

const linkButton = "font-medium text-primary underline underline-offset-2 hover:brightness-125 text-[0.88rem]";
const panel = "grid min-w-0 gap-2.5 rounded-lg border bg-muted px-4 py-3.5";

const scenarioLabel = (s: DummyScenario) => `${capitalize(s.reason)} · Tk ${formatNumber(s.amount)} · ${s.vehicle}`;

/** The main call to action: paste a notice URL. Reading external pages is not available, so it offers a sample notice. */
export function UrlCard() {
  const input = useRef<HTMLInputElement>(null);
  const flow = useAnalysisFlow();
  const [url, setUrl] = useState("");
  const [error, setError] = useState("");
  const [state, setState] = useState<PanelState>("idle");
  const [scenarios, setScenarios] = useState<DummyScenario[] | null>(null);
  const [scenarioError, setScenarioError] = useState("");
  const [key, setKey] = useState("speed");

  // Links such as /dashboard#notice land with the field ready to type in.
  useEffect(() => {
    if (window.location.hash === "#notice") input.current?.focus();
  }, []);

  // The sample list comes from the service, so load it the first time a sample is offered.
  useEffect(() => {
    if ((state !== "unsupported" && state !== "example") || scenarios) return;
    getScenarios()
      .then((list) => {
        setScenarios(list);
        if (list.length && !list.some((s) => s.key === "speed")) setKey(list[0].key);
      })
      .catch((e) => setScenarioError(e instanceof Error ? e.message : "Could not load the sample notices."));
  }, [state, scenarios]);

  function submit(e: React.FormEvent) {
    e.preventDefault();
    if (state === "checking") return;
    const message = checkNoticeUrl(url);
    if (message) {
      setError(message);
      setState("idle");
      input.current?.focus();
      return;
    }
    setError("");
    setState("checking");
    // Reading an external page is not available yet, so the answer is always the same.
    window.setTimeout(() => setState((s) => (s === "checking" ? "unsupported" : s)), 700);
  }

  function runSample(enteredUrl?: string) {
    void flow.run(async (setStage) => {
      setStage("analysing");
      return (await analyzeSample({ url: enteredUrl || undefined, scenario: key })).id;
    });
  }

  if (flow.busy) {
    return (
      <section className="rounded-[10px] border bg-card p-5">
        <h2 className="mb-4 text-center text-xl font-semibold">Checking the notice</h2>
        <ProcessingSteps stage={flow.stage} withUpload={false} />
      </section>
    );
  }

  const checking = state === "checking";
  const chosen = scenarios?.find((s) => s.key === key) ?? scenarios?.[0];
  const picker = (
    <label className="grid max-w-[420px] gap-1 text-[0.78rem] font-medium text-muted-foreground">
      Sample scenario
      <NativeSelect value={key} onChange={(e) => setKey(e.target.value)} disabled={!scenarios}>
        {(scenarios ?? []).map((s) => (
          <option key={s.key} value={s.key}>
            {scenarioLabel(s)}
          </option>
        ))}
      </NativeSelect>
      {scenarioError && <span role="alert" className="font-normal text-bad">{scenarioError}</span>}
    </label>
  );

  return (
    <section id="notice" aria-labelledby="notice-title" className="grid scroll-mt-20 gap-3 rounded-[10px] border bg-card p-5">
      <h2 id="notice-title" className="font-sans text-[1.25rem] leading-[1.3] font-semibold">
        Check a Traffic Fine Notice
      </h2>
      <p className="max-w-[70ch] text-muted-foreground">
        Paste the URL of your traffic fine notice to review the offence details and check them against the configured legal rules.
      </p>

      <form onSubmit={submit} noValidate className="grid gap-1.5">
        <label htmlFor="notice-url" className="text-[0.8rem] font-medium text-muted-foreground">
          Notice URL
        </label>
        <div className="flex flex-col gap-2 sm:flex-row sm:items-stretch">
          <Input
            ref={input}
            id="notice-url"
            type="text"
            inputMode="url"
            autoComplete="off"
            spellCheck={false}
            placeholder="https://example.com/traffic-fine-notice"
            value={url}
            readOnly={checking}
            aria-invalid={error ? true : undefined}
            aria-describedby="notice-help notice-error"
            className={cn("h-11 flex-1 text-[0.95rem]", error && "border-bad")}
            onChange={(e) => {
              setUrl(e.target.value);
              if (error) setError("");
              if (state === "unsupported") setState("idle");
            }}
          />
          <button type="submit" disabled={checking} aria-busy={checking} className={cn(amberButton, sizeLg, "gap-2 px-[22px] disabled:cursor-not-allowed disabled:opacity-50")}>
            {checking ? (
              <>
                <span aria-hidden="true" className="inline-block size-3.5 animate-spin rounded-full border-2 border-current border-t-transparent" />
                Checking&hellip;
              </>
            ) : (
              "Analyze Notice"
            )}
          </button>
        </div>
        <p id="notice-error" role="alert" className="m-0 text-sm text-bad empty:hidden">
          {error}
        </p>
        <p id="notice-help" className="max-w-[70ch] text-[0.82rem] text-muted-foreground">
          The URL must point to a notice or page that contains the traffic fine details, such as the offence, section and amount.
        </p>
      </form>

      <div className="flex flex-wrap items-center gap-2">
        <button type="button" className={linkButton} onClick={() => setState("example")}>
          View an example notice
        </button>
        <span className="text-muted-foreground" aria-hidden="true">
          &middot;
        </span>
        <Link href="/upload" className={linkButton}>
          Upload a receipt instead
        </Link>
      </div>

      {state === "unsupported" && (
        <div role="status" className={panel}>
          <b>External URL fetching is not enabled in this prototype.</b>
          <p className="max-w-[70ch] text-[0.92rem]">
            Nirapod Fine cannot read the page at <span className="font-mono text-xs break-all text-muted-foreground">{shortUrl(url.trim())}</span>, so no result was produced from it. You can continue with an illustrative sample notice to see how a result looks. The sample is not your notice.
          </p>
          {picker}
          <div className="flex flex-wrap gap-2">
            <button type="button" className={cn(amberButton, "px-4 py-2 text-sm")} disabled={!scenarios} onClick={() => runSample(url.trim())}>
              Continue with sample notice
            </button>
            <button
              type="button"
              className="rounded-md border border-primary px-4 py-2 text-sm font-medium text-primary hover:bg-accent"
              onClick={() => {
                setState("idle");
                input.current?.focus();
              }}
            >
              Edit URL
            </button>
          </div>
        </div>
      )}

      {state === "example" && (
        <div className={panel}>
          <b>Example notice</b>
          <p className="max-w-[70ch] text-[0.92rem]">An illustrative sample. It is not a real notice and not your data.</p>
          {picker}
          {chosen && (
            <div className="max-w-[420px]">
              <ReceiptPaper
                data={{ reason: chosen.reason, amount: chosen.amount, date: chosen.date, location: chosen.location, vehicle_type: chosen.vehicle, receipt_number: chosen.receipt_number, section: chosen.section || null, notes: chosen.notes || null }}
              />
            </div>
          )}
          <div className="flex flex-wrap gap-2">
            <button type="button" className={cn(amberButton, "px-4 py-2 text-sm")} disabled={!scenarios} onClick={() => runSample()}>
              Analyze this sample
            </button>
            <button type="button" className="rounded-md border border-primary px-4 py-2 text-sm font-medium text-primary hover:bg-accent" onClick={() => setState("idle")}>
              Close
            </button>
          </div>
        </div>
      )}
      {flow.error && (
        <p role="alert" className="text-sm text-bad">
          {flow.error}
        </p>
      )}
    </section>
  );
}

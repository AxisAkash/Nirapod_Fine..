"use client";

import { useState } from "react";
import { Plus, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { KeywordItem } from "@/types/api";

/** An editable list of short strings (aliases, vehicle names, condition notes). */
export function StringListEditor({
  id,
  items,
  onChange,
  readOnly,
  placeholder,
}: {
  id: string;
  items: string[];
  onChange: (items: string[]) => void;
  readOnly?: boolean;
  placeholder?: string;
}) {
  const [draft, setDraft] = useState("");
  const add = () => {
    const v = draft.trim();
    if (v && !items.includes(v)) onChange([...items, v]);
    setDraft("");
  };
  return (
    <div className="grid gap-2">
      {items.length > 0 && (
        <ul className="flex flex-wrap gap-1.5">
          {items.map((it) => (
            <li key={it} className="flex items-center gap-1 rounded-md bg-muted py-0.5 pr-1 pl-2 text-xs">
              {it}
              {!readOnly && (
                <button type="button" aria-label={`Remove ${it}`} className="rounded p-0.5 hover:bg-border" onClick={() => onChange(items.filter((x) => x !== it))}>
                  <X className="size-3" />
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
      {!readOnly && (
        <div className="flex gap-2">
          <Input
            id={id}
            value={draft}
            placeholder={placeholder}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                add();
              }
            }}
          />
          <Button type="button" variant="outline" onClick={add} aria-label="Add">
            <Plus />
          </Button>
        </div>
      )}
    </div>
  );
}

/** Editable keyword list with a weight for each word. */
export function KeywordEditor({ items, onChange, readOnly }: { items: KeywordItem[]; onChange: (items: KeywordItem[]) => void; readOnly?: boolean }) {
  const [word, setWord] = useState("");
  const [weight, setWeight] = useState("20");
  const add = () => {
    const w = word.trim();
    const wt = Math.max(1, Math.min(100, Number(weight) || 10));
    if (w && !items.some((k) => k.word === w)) onChange([...items, { word: w, weight: wt }]);
    setWord("");
  };
  return (
    <div className="grid gap-2">
      {items.length > 0 && (
        <ul className="flex flex-wrap gap-1.5">
          {items.map((k) => (
            <li key={k.word} className="flex items-center gap-1 rounded-md bg-muted py-0.5 pr-1 pl-2 text-xs">
              {k.word} <span className="font-mono text-muted-foreground">{k.weight}</span>
              {!readOnly && (
                <button type="button" aria-label={`Remove ${k.word}`} className="rounded p-0.5 hover:bg-border" onClick={() => onChange(items.filter((x) => x.word !== k.word))}>
                  <X className="size-3" />
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
      {!readOnly && (
        <div className="flex gap-2">
          <Input
            aria-label="Keyword"
            value={word}
            placeholder="Keyword"
            onChange={(e) => setWord(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                add();
              }
            }}
          />
          <Input aria-label="Weight" className="w-20" inputMode="numeric" value={weight} onChange={(e) => setWeight(e.target.value)} />
          <Button type="button" variant="outline" onClick={add} aria-label="Add keyword">
            <Plus />
          </Button>
        </div>
      )}
    </div>
  );
}

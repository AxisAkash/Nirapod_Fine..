/** Landing page content. Icon names refer to LandingIcon. */
export type LandingIconName =
  | "match" | "limit" | "doc" | "docok" | "gauge" | "light" | "grid" | "repeat" | "shield" | "ok" | "alert" | "help" | "menu" | "close";

export interface Tile {
  icon: LandingIconName;
  title: string;
  text: string;
}

export const CAPABILITIES: Tile[] = [
  { icon: "match", title: "Offence & Section Matching", text: "Connect the reported offence with a potentially applicable legal provision." },
  { icon: "limit", title: "Fine Limit Validation", text: "Compare the stated fine with the configured legal limit." },
  { icon: "doc", title: "Explainable Results", text: "Present the relevant evidence and explain why a case may need review." },
];

export const SITUATIONS: Tile[] = [
  { icon: "gauge", title: "Speed limit violations", text: "Compare a recorded speeding fine with the limit configured for the matched section." },
  { icon: "docok", title: "Driving without required documentation", text: "Licence, registration, fitness or tax token offences that appear in the dataset." },
  { icon: "light", title: "Traffic signal violations", text: "Signal and sign offences, checked against the configured fine range." },
  { icon: "grid", title: "Other offences in the dataset", text: "Parking, overloading, horn use and others. Coverage follows the configured dataset only." },
];

export const CHECKS: Tile[] = [
  { icon: "match", title: "Offence and Section", text: "Does the stated offence correspond to the selected legal provision?" },
  { icon: "limit", title: "Fine Limit", text: "Is the recorded amount within the configured maximum?" },
  { icon: "repeat", title: "Repeat-Offence Rule", text: "Does the relevant repeat-offence rule apply to the available information?" },
  { icon: "shield", title: "Exceptions", text: "Could an applicable exception or exemption change the assessment?" },
];

export const STEPS = [
  { no: "01", title: "Upload Your Receipt", text: "Upload a traffic fine or mamla receipt for review." },
  { no: "02", title: "Check the Details", text: "The prototype examines the offence details, relevant section, configured fine limits, and applicable exception rules." },
  { no: "03", title: "Understand the Result", text: "Review the findings, supporting legal references, and any issues that may require further verification." },
];

export const OUTCOMES = [
  { tone: "ok", icon: "ok", label: "Consistent", text: "No discrepancy was identified by the configured checks." },
  { tone: "warn", icon: "alert", label: "Review Required", text: "A possible discrepancy or missing detail needs further examination." },
  { tone: "neutral", icon: "help", label: "Insufficient Information", text: "The available receipt details are not enough to reach a meaningful assessment." },
] as const;

export const HERO_CAPS = ["Section Matching", "Fine Limit Checks", "Explainable Results"];

export const FOOTER_LINKS = [
  { id: "overview", label: "Capabilities" },
  { id: "situations", label: "Situations" },
  { id: "how", label: "How It Works" },
  { id: "checks", label: "What We Check" },
  { id: "results", label: "Possible Results" },
];

export const DISCLAIMER =
  "Nirapod Fine is a research prototype that provides informational assessments, not legal advice or an official government determination. Verify applicable requirements against the official Road Transport Act, 2018, and relevant legal sources.";

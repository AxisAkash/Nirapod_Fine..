export interface NavItem {
  href: string;
  label: string;
  adminOnly?: boolean;
}

/** Signed-in navigation. */
export const APP_NAV: NavItem[] = [
  { href: "/dashboard", label: "Overview" },
  { href: "/checks", label: "Recent Checks" },
  { href: "/how-it-works", label: "How It Works" },
  { href: "/admin/dataset", label: "Admin dataset", adminOnly: true },
];

/** Landing page section links (scroll targets). */
export const LANDING_NAV = [
  { id: "how", label: "How It Works" },
  { id: "situations", label: "Situations" },
  { id: "checks", label: "What We Check" },
];

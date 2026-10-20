import type { ComponentProps } from "react";
import type { ClerkProvider } from "@clerk/nextjs";

/** Makes Clerk's sign-in and account screens match the app (light theme, green accent, IBM Plex). */
export const clerkAppearance: ComponentProps<typeof ClerkProvider>["appearance"] = {
  variables: {
    colorPrimary: "#2f6b4f",
    colorBackground: "#ffffff",
    colorForeground: "#17211c",
    colorMutedForeground: "#5a665f",
    colorDanger: "#a3262a",
    borderRadius: "0.5rem",
    fontFamily: "var(--font-plex-sans), system-ui, sans-serif",
  },
};

import type { ComponentProps } from "react";
import type { ClerkProvider } from "@clerk/nextjs";

/** Makes Clerk's sign-in and account screens match the app (light theme, blue accent, IBM Plex). */
export const clerkAppearance: ComponentProps<typeof ClerkProvider>["appearance"] = {
  variables: {
    colorPrimary: "#1d4f91",
    colorBackground: "#ffffff",
    colorForeground: "#16202e",
    colorMutedForeground: "#5b6678",
    colorDanger: "#a3262a",
    borderRadius: "0.5rem",
    fontFamily: "var(--font-plex-sans), system-ui, sans-serif",
  },
};

import "server-only";

/** Where the FastAPI backend lives. Only the Next.js server talks to it; the browser never does. */
export const BACKEND_URL = (process.env.BACKEND_URL ?? "http://localhost:8000").replace(/\/$/, "");

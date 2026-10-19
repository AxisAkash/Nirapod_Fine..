import { clerkMiddleware } from "@clerk/nextjs/server";

// Everything except the landing page and the sign-in screens needs a signed-in user.
const PROTECTED_PREFIXES = ["/dashboard", "/upload", "/cases", "/dummy-url", "/admin"];

const isProtected = (req: { nextUrl: { pathname: string } }) =>
  PROTECTED_PREFIXES.some((prefix) => req.nextUrl.pathname === prefix || req.nextUrl.pathname.startsWith(`${prefix}/`));

export default clerkMiddleware(async (auth, req) => {
  if (isProtected(req)) await auth.protect();
});

export const config = {
  matcher: [
    // Skip Next.js internals and static files
    "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
    "/(api|trpc)(.*)",
  ],
};

import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";

// Everything except the landing page and the sign-in screens needs a signed-in user.
const isProtected = createRouteMatcher(["/dashboard(.*)", "/upload(.*)", "/cases(.*)", "/dummy-url(.*)", "/admin(.*)"]);

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

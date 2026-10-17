import { auth } from "@clerk/nextjs/server";

import { BACKEND_URL } from "@/config/env";

/**
 * Browser -> this route -> FastAPI. The route adds the signed-in user's Clerk token on the server, so the token
 * never reaches page scripts and the backend needs no CORS setup.
 */
const ALLOWED = new Set(["me", "cases", "receipts", "dummy-url", "offence-rules", "admin"]);
const PASS_HEADERS = ["content-type", "content-disposition", "cache-control"];

function json(detail: string, status: number) {
  return Response.json({ detail }, { status });
}

async function forward(req: Request, ctx: RouteContext<"/api/backend/[...path]">) {
  const { path } = await ctx.params;
  if (!ALLOWED.has(path[0])) return json("Not found", 404);

  // Mutating requests must come from this site (the session cookie alone is not proof of intent).
  if (req.method !== "GET" && req.method !== "HEAD") {
    const origin = req.headers.get("origin");
    if (origin && new URL(origin).host !== new URL(req.url).host) return json("Cross-site request refused", 403);
  }

  const { getToken } = await auth();
  const token = await getToken();
  if (!token) return json("Not signed in", 401);

  const headers = new Headers({ Authorization: `Bearer ${token}` });
  const contentType = req.headers.get("content-type");
  if (contentType) headers.set("content-type", contentType);
  const hasBody = req.method !== "GET" && req.method !== "HEAD";

  let upstream: Response;
  try {
    upstream = await fetch(`${BACKEND_URL}/api/${path.map(encodeURIComponent).join("/")}${new URL(req.url).search}`, {
      method: req.method,
      headers,
      body: hasBody ? await req.arrayBuffer() : undefined,
      cache: "no-store",
    });
  } catch {
    return json("The service is not reachable. Try again in a moment.", 503);
  }

  const out = new Headers();
  for (const h of PASS_HEADERS) {
    const v = upstream.headers.get(h);
    if (v) out.set(h, v);
  }
  return new Response(upstream.status === 204 ? null : upstream.body, { status: upstream.status, headers: out });
}

export { forward as GET, forward as POST, forward as PUT, forward as DELETE };

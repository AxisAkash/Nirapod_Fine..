import "server-only";
import { auth } from "@clerk/nextjs/server";

import { BACKEND_URL } from "@/config/env";
import { ApiError, messageFromBody } from "@/services/api-error";

/** Calls the backend from a server component or route handler, sending the signed-in user's Clerk token. */
export async function backendGet<T>(path: string): Promise<T> {
  const { getToken } = await auth();
  const token = await getToken();
  if (!token) throw new ApiError("Not signed in", 401);
  let res: Response;
  try {
    res = await fetch(`${BACKEND_URL}/api${path}`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
    });
  } catch {
    throw new ApiError("The service is not reachable. Try again in a moment.", 503);
  }
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new ApiError(messageFromBody(body, `Request failed (${res.status})`), res.status);
  }
  return (await res.json()) as T;
}

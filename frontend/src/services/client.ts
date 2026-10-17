import { ApiError, messageFromBody } from "@/services/api-error";

/** Browser-side calls go to the Next.js proxy (/api/backend/...), which adds the Clerk token on the server. */
export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const isForm = typeof FormData !== "undefined" && init.body instanceof FormData;
  let res: Response;
  try {
    res = await fetch(`/api/backend${path}`, {
      ...init,
      headers: isForm || !init.body ? init.headers : { "Content-Type": "application/json", ...init.headers },
    });
  } catch {
    throw new ApiError("Could not reach the service. Check your connection and try again.", 503);
  }
  if (res.status === 204) return undefined as T;
  const body = await res.json().catch(() => null);
  if (!res.ok) throw new ApiError(messageFromBody(body, `Something went wrong (${res.status})`), res.status);
  return body as T;
}

export const jsonBody = (data: unknown): RequestInit => ({ body: JSON.stringify(data) });

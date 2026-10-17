/** Checks a pasted notice URL. Returns a message for the user, or an empty string when the address is acceptable. */
export function checkNoticeUrl(input: string): string {
  const v = input.trim();
  if (!v) return "Enter the URL of your traffic fine notice.";
  if (/\s/.test(v)) return "A web address cannot contain spaces.";
  let u: URL;
  try {
    u = new URL(v);
  } catch {
    return /^[\w-]+(\.[\w-]+)+/.test(v)
      ? "Start the address with http:// or https://."
      : "This does not look like a web address. Use a link such as https://example.com/traffic-fine-notice.";
  }
  if (u.protocol !== "http:" && u.protocol !== "https:") return "Only http:// and https:// links are accepted.";
  if (u.hostname.indexOf(".") < 1) return "The address needs a full domain name, such as example.com.";
  return "";
}

/** A link target that is safe to put in an href: only http(s) addresses, otherwise undefined. */
export function safeHref(u: string | null | undefined): string | undefined {
  if (!u) return undefined;
  try {
    const x = new URL(u);
    return x.protocol === "http:" || x.protocol === "https:" ? x.toString() : undefined;
  } catch {
    return undefined;
  }
}

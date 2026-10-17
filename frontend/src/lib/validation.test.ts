import { describe, expect, it } from "vitest";

import { checkNoticeUrl, safeHref } from "@/lib/validation";

describe("checkNoticeUrl", () => {
  it("accepts ordinary http and https addresses", () => {
    expect(checkNoticeUrl("https://example.com/traffic-fine-notice")).toBe("");
    expect(checkNoticeUrl("  http://notices.dmp.gov.bd/case/123?x=1  ")).toBe("");
  });

  it("asks for a value when empty", () => {
    expect(checkNoticeUrl("")).toMatch(/Enter the URL/);
    expect(checkNoticeUrl("   ")).toMatch(/Enter the URL/);
  });

  it("rejects spaces", () => {
    expect(checkNoticeUrl("https://example.com/my notice")).toMatch(/spaces/);
  });

  it("tells the user to add the scheme when it is missing", () => {
    expect(checkNoticeUrl("example.com/notice")).toMatch(/http:\/\/ or https:\/\//);
  });

  it("rejects text that is not an address", () => {
    expect(checkNoticeUrl("my traffic fine")).toMatch(/spaces/);
    expect(checkNoticeUrl("hello")).toMatch(/does not look like a web address/);
  });

  it("only accepts http and https", () => {
    expect(checkNoticeUrl("ftp://example.com/file")).toMatch(/Only http/);
    expect(checkNoticeUrl("javascript:alert(1)")).toMatch(/Only http/);
  });

  it("needs a full domain name", () => {
    expect(checkNoticeUrl("https://localhost/notice")).toMatch(/full domain/);
  });
});

describe("safeHref", () => {
  it("passes http(s) addresses through", () => {
    expect(safeHref("https://example.com/a")).toBe("https://example.com/a");
  });
  it("refuses other schemes, bad input and empty values", () => {
    expect(safeHref("javascript:alert(1)")).toBeUndefined();
    expect(safeHref("data:text/html,<b>x</b>")).toBeUndefined();
    expect(safeHref("not a url")).toBeUndefined();
    expect(safeHref(null)).toBeUndefined();
    expect(safeHref("")).toBeUndefined();
  });
});

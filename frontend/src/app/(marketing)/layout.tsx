import { Suspense } from "react";

import { MarketingHeader } from "@/components/layouts/marketing-header";
import { MarketingHeaderView } from "@/components/layouts/marketing-header-view";
import { SiteFooter } from "@/components/layouts/site-footer";

export default function MarketingLayout({ children }: LayoutProps<"/">) {
  return (
    <>
      {/* Whether the visitor is signed in is only known per request, so the header streams in. */}
      <Suspense fallback={<MarketingHeaderView signedIn={false} />}>
        <MarketingHeader />
      </Suspense>
      <div className="flex-1">{children}</div>
      <SiteFooter />
    </>
  );
}

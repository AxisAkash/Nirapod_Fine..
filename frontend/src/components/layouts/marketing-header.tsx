import { auth } from "@clerk/nextjs/server";

import { MarketingHeaderView } from "@/components/layouts/marketing-header-view";

export async function MarketingHeader() {
  const { userId } = await auth();
  return <MarketingHeaderView signedIn={!!userId} />;
}

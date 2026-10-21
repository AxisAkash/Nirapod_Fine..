import { redirect } from "next/navigation";

/** Everything about a case is on its result page now. This keeps old links working. */
export default async function CaseRecordPage({ params }: PageProps<"/cases/[id]">) {
  const { id } = await params;
  redirect(`/cases/${id}/result`);
}

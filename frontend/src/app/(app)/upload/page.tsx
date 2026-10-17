import type { Metadata } from "next";

import { UploadForm } from "@/components/features/upload/upload-form";
import { PageHeader } from "@/components/layouts/page-header";

export const metadata: Metadata = { title: "Check a receipt" };

export default function UploadPage() {
  return (
    <>
      <PageHeader eyebrow="New check" title="Upload a mamla receipt" />
      <UploadForm />
    </>
  );
}

import { redirect } from "next/navigation";

/** Uploading now happens on the Overview page. This keeps old links working. */
export default function UploadPage() {
  redirect("/dashboard#notice");
}

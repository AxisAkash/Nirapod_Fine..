import { Logo } from "@/components/layouts/logo";

export default function AuthLayout({ children }: LayoutProps<"/">) {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-8 px-4 py-10">
      <Logo href="/" />
      {children}
    </main>
  );
}

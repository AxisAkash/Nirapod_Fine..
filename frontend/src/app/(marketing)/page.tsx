import { Hero } from "@/components/features/landing/hero";
import { Capabilities, Checks, CtaBand, HowItWorks, Outcomes, Situations } from "@/components/features/landing/sections";

export default function LandingPage() {
  return (
    <main>
      <Hero />
      <Capabilities />
      <Situations />
      <HowItWorks />
      <Checks />
      <Outcomes />
      <CtaBand />
    </main>
  );
}

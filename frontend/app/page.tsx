import Link from "next/link";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/theme-toggle";

export default function HomePage() {
  return (
    <main className="relative flex min-h-screen flex-col items-center justify-center gap-6 px-6 text-center">
      <div className="absolute right-4 top-4">
        <ThemeToggle />
      </div>
      <div className="flex items-center gap-3">
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-clinic-900 font-display text-xl text-white">
          W
        </div>
        <div className="text-left">
          <p className="font-display text-2xl font-semibold text-clinic-950">Watan Hospital</p>
          <p className="text-sm tracking-wide text-clinic-700">Doctor Copilot</p>
        </div>
      </div>
      <p className="max-w-md text-sm text-ink/70">
        AI-assisted prescription drafting with real-time drug-interaction safety checks.
      </p>
      <Button asChild size="lg">
        <Link href="/login">Sign in to continue</Link>
      </Button>
    </main>
  );
}

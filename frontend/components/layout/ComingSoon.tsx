import type { LucideIcon } from "lucide-react";

interface ComingSoonProps {
  icon: LucideIcon;
  title: string;
  description: string;
}

export function ComingSoon({ icon: Icon, title, description }: ComingSoonProps) {
  return (
    <div className="flex h-full min-h-[60vh] flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-border text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-clinic-800/10 text-clinic-800 dark:bg-vitals-pulse/10 dark:text-vitals-pulse">
        <Icon className="h-5 w-5" />
      </div>
      <div>
        <p className="font-display text-base font-semibold text-ink">{title}</p>
        <p className="mt-1 max-w-sm text-sm text-ink/50">{description}</p>
      </div>
    </div>
  );
}

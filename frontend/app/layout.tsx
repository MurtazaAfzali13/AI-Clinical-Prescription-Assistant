import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Watan Hospital | Doctor Copilot",
  description: "AI-assisted prescription drafting and drug-interaction safety checks.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="app-shell-bg min-h-screen font-body antialiased">{children}</body>
    </html>
  );
}

import type { Metadata } from "next";
import { IBM_Plex_Sans, Libre_Baskerville } from "next/font/google";
import { Providers } from "@/components/providers/providers";
import { cn } from "@/lib/utils";
import "./globals.css";

const sans = IBM_Plex_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-ibm-plex",
});

const display = Libre_Baskerville({
  subsets: ["latin"],
  weight: ["700"],
  variable: "--font-libre",
});

export const metadata: Metadata = {
  title: "Legal Copilot",
  description:
    "Understand legal documents with cited answers, risk highlights, and consultation prep — legal information, not legal advice.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={cn(sans.variable, display.variable)}
    >
      <body className={cn(sans.className, "min-h-screen antialiased")}>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}

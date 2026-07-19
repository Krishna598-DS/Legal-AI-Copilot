import type { Metadata } from "next";
import { IBM_Plex_Sans, Libre_Baskerville } from "next/font/google";
import "./globals.css";

const sans = IBM_Plex_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-sans",
});

const display = Libre_Baskerville({
  subsets: ["latin"],
  weight: ["700"],
  variable: "--font-display",
});

export const metadata: Metadata = {
  title: "AI Legal Copilot",
  description:
    "Understand legal documents, explain contracts, detect risks, prepare for consultations, and connect with the right legal professionals.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${sans.className} ${sans.variable} ${display.variable} antialiased`}>
        {children}
      </body>
    </html>
  );
}

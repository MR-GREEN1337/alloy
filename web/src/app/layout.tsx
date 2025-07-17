import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { AppProviders } from "@/components/global/providers";
import { Toaster } from "@/components/ui/sonner";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Alloy",
  description: "The Cultural Due Diligence Platform",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  // This is a Server Component, so it can safely access process.env at runtime.
  // We use the same variable name for consistency.
  const apiUrl = process.env.NEXT_PUBLIC_API_URL;

  if (!apiUrl) {
    // This will cause an error page in production if the env var is missing,
    // which is better than a broken app.
    throw new Error("FATAL: NEXT_PUBLIC_API_URL environment variable is not set.");
  }

  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        <AppProviders apiUrl={apiUrl}>{children}</AppProviders>
      <Toaster richColors position="bottom-right" />
      </body>
    </html>
  );
}
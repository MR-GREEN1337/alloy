import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { NextAuthProvider } from "@/components/global/providers";
import Footer from "@/components/global/Footer";

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
  const footerLeftLinks = [
    { href: "#", label: "Affinity Overlap Score" },
    { href: "#", label: "Culture Clash Report" },
    { href: "#", label: "Untapped Growth Analysis" },
    { href: "#", label: "AI-Powered Brand Archetyping" },
  ];
  const footerRightLinks = [
    { href: "/login", label: "Log In" },
    { href: "/login", label: "Request a Demo" },
    { href: "https://devpost.com/software/alloy-cultural-due-diligence", label: "Devpost Hackathon Submission" },
  ];
  const problemStatement = "M&A failures are costly, often rooted in unforeseen cultural clashes. Billions are lost when executive 'gut feel' misses the mark on brand incompatibility.";
  const solutionStatement = "Alloy replaces guesswork with data. We provide a quantifiable Cultural Compatibility Score by analyzing audience taste profiles, de-risking acquisitions and illuminating the human element of a deal.";

  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased bg-black`}
      >
        <NextAuthProvider>{children}</NextAuthProvider>
        <Footer
          leftLinks={footerLeftLinks}
          rightLinks={footerRightLinks}
          copyrightText="The Cultural Due Diligence Platform."
          problemStatement={problemStatement}
          solutionStatement={solutionStatement}
        />
      </body>
    </html>
  );
}
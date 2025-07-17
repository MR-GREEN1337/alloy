"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { useAuth } from "@/components/global/providers";
import { Sidebar } from "@/components/global/Sidebar";
import { ThemeProvider as NextThemesProvider } from "next-themes";
import { Header } from "@/components/global/Header";
import { PageLoader } from "@/components/global/PageLoader";

export default function AuthedLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.replace('/login');
    }
  }, [isLoading, isAuthenticated, router]);

  if (isLoading || !isAuthenticated) {
    return <PageLoader />;
  }

  return (
    <NextThemesProvider
        attribute="class"
        defaultTheme="system"
        enableSystem
        disableTransitionOnChange
    >
        <div className="flex min-h-screen w-full flex-col bg-background">
            <Sidebar />
            <div className="flex flex-col sm:pl-14">
                <Header />
                <main className="grid flex-1 items-start gap-4 p-4 sm:px-6 sm:py-4 md:gap-8">
                    {children}
                </main>
            </div>
        </div>
    </NextThemesProvider>
  );
}
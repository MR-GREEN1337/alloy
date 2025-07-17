"use client";

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/components/global/providers';
import { AuthVisual } from "@/components/auth/AuthVisual";
import Logo from "@/components/global/Logo";
import Link from "next/link";
import { PageLoader } from '@/components/global/PageLoader';

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    // Wait for the auth state to be determined
    if (!isLoading && isAuthenticated) {
      // If user is authenticated, redirect them to the dashboard
      router.replace('/dashboard');
    }
  }, [isLoading, isAuthenticated, router]);

  // While loading or if authenticated (and about to be redirected), show a loading screen
  if (isLoading || isAuthenticated) {
    return <PageLoader />;
  }

  // Only show the auth layout if the user is not authenticated
  return (
    <div className="bg-background text-foreground relative flex min-h-screen w-full font-sans">
      <div className="absolute top-6 left-6 z-10">
        <Logo className="text-foreground" />
      </div>
      
      <div className="flex flex-1 flex-col justify-center items-center gap-6 p-4 lg:p-8">
        <main className="w-full max-w-sm">{children}</main>
        <footer className="w-full max-w-sm text-center text-muted-foreground text-xs">
          <Link href="#" className="hover:text-foreground">
            Terms of Service
          </Link>
          {" | "}
          <Link href="#" className="hover:text-foreground">
            Privacy Policy
          </Link>
        </footer>
      </div>
      <div className="hidden lg:flex lg:flex-1">
        <AuthVisual />
      </div>
    </div>
  );
}
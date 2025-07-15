"use client";

import { useSearchParams, useRouter } from 'next/navigation';
import { useEffect } from 'react';
import { useAuth } from '@/components/global/providers';

export default function TokenPage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const { login } = useAuth();

  useEffect(() => {
    const accessToken = searchParams.get('access_token');
    const refreshToken = searchParams.get('refresh_token');

    if (accessToken && refreshToken) {
      login(accessToken, refreshToken);
      // Clean the URL and redirect to the dashboard
      router.replace('/dashboard');
    } else {
      // Handle error case, maybe redirect to login with an error message
      router.replace('/login?error=auth_failed');
    }
  }, [searchParams, router, login]);

  return (
    <div className="flex h-screen w-full items-center justify-center bg-background">
      <div className="text-center">
        <p className="text-lg text-foreground">Finalizing authentication...</p>
        <p className="text-sm text-muted-foreground">Please wait, you will be redirected shortly.</p>
      </div>
    </div>
  );
}
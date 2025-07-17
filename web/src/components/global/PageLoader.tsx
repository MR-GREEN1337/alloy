"use client";

import { Loader2 } from "lucide-react";

/**
 * A full-page loader component that displays a centered spinning icon.
 * Ideal for indicating the initial loading state of the application.
 */
export const PageLoader = () => {
  return (
    <div className="flex h-screen w-full items-center justify-center bg-background">
      <Loader2 className="h-8 w-8 animate-spin text-primary" />
    </div>
  );
};
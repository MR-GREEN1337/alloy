"use client";

import React from "react";
import Link from "next/link";
import { Playfair_Display } from "next/font/google";
import { cn } from "@/lib/utils";
import { usePathname } from "next/navigation";

// Initialize the Playfair Display font for an elegant, premium wordmark.
const playfair = Playfair_Display({
  subsets: ["latin"],
  weight: "700", // A bold weight provides presence and authority.
});

interface LogoProps {
  /**
   * Additional CSS classes to apply to the main link element.
   * Use this to control color, etc. e.g., 'text-white' or 'text-foreground'.
   */
  className?: string;

  /**
   * Whether to hide the text part of the logo.
   * @default false
   */
  hideText?: boolean;
}

/**
 * The Alloy Logo Component.
 *
 * Renders the complete Alloy logotype: a custom SVG icon that fuses the letter 'A'
 * with a diamond shape, followed by the "Alloy" wordmark in an elegant serif font.
 * The entire component is theme-aware and interactive.
 */
export const Logo: React.FC<LogoProps> = ({ className, hideText = false }) => {
  const pathname = usePathname();
  return (
    <Link
      href={pathname.startsWith("/dashboard") ? "/dashboard" : "/"}
      className={cn(
        "group flex items-center gap-2.5 transition-opacity duration-300 hover:opacity-80",
        className,
      )}
      aria-label="Alloy Homepage"
    >
      {/* The Custom Alloy SVG Icon */}
      <div className="h-7 w-7">
        <svg
          viewBox="0 0 40 40"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          aria-hidden="true"
          className="h-full w-full transition-transform duration-300 ease-in-out group-hover:rotate-[-5deg] group-hover:scale-105"
        >
          {/* Outer Diamond */}
          <path
            d="M20 4L36 20L20 36L4 20Z"
            stroke="currentColor"
            strokeWidth="3"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          {/* Inner 'A' shape / Gem Facet */}
          <path
            d="M20 12V28M12 20H28"
            stroke="currentColor"
            strokeWidth="3"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </div>

      {/* The "Alloy" Wordmark */}
      {!hideText && (
        <span
          className={cn(
            playfair.className, // Apply the elegant Playfair Display font
            "text-2xl",         // Set a default size for the text
          )}
        >
          Alloy
        </span>
      )}
    </Link>
  );
};

export default Logo;
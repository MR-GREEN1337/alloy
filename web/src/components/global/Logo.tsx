"use client";

import React from "react";
import Link from "next/link";
import { Playfair_Display } from "next/font/google";
import { cn } from "@/lib/utils";
import { usePathname } from "next/navigation";

const playfair = Playfair_Display({
  subsets: ["latin"],
  weight: "700",
});

interface LogoProps {
  className?: string;
  hideText?: boolean;
}

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
      <div className="h-7 w-7">
        <svg
          viewBox="0 0 40 40"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          aria-hidden="true"
          className="h-full w-full transition-transform duration-300 ease-in-out group-hover:rotate-[-5deg] group-hover:scale-105"
        >
          <path d="M20 4L36 20L20 36L4 20Z" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
          <path d="M20 12V28M12 20H28" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </div>
    </Link>
  );
};

export default Logo;
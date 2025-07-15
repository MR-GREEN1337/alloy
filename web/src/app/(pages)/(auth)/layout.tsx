import { AuthVisual } from "@/components/auth/AuthVisual";
import Logo from "@/components/global/Logo";
import Link from "next/link";

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
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
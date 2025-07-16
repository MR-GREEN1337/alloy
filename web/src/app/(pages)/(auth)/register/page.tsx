"use client";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import Link from "next/link";
import { useState, FormEvent } from "react";
import { FaGoogle } from "react-icons/fa";
import Logo from "@/components/global/Logo";
import { useAuth } from "@/components/global/providers";
import { useRouter } from 'next/navigation';

export default function RegisterPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const { login } = useAuth();
  const router = useRouter();

  const handleRegister = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);

    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    const formData = new URLSearchParams();
    formData.append('username', email);
    formData.append('password', password);

    try {
      // 1. Register the user
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/auth/register`, {
        method: 'POST',
        body: JSON.stringify({ email, password, full_name: "" }),
        headers: { 'Content-Type': 'application/json' }
      });

      if (!res.ok) {
        const errorData = await res.json();
        setError(errorData.detail || "Registration failed.");
        return;
      }
      
      // 2. Log the user in to get tokens
      const loginRes = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: formData.toString(),
      })

      if (!loginRes.ok) {
        throw new Error("Registration successful, but login failed. Please log in manually.");
      }

      const tokens = await loginRes.json();
      login(tokens.access_token, tokens.refresh_token);
      router.push("/dashboard");

    } catch (err) {
      setError(err instanceof Error ? err.message : "An unexpected error occurred. Please try again.");
    }
  };
  const googleAuthUrl = `${process.env.NEXT_PUBLIC_API_URL}/auth/google/authorize`;

  return (
    <Card className="w-full max-w-sm">
      <CardHeader className="text-center">
        <Logo className="mx-auto" />
        <CardTitle className="text-2xl">Create an Account</CardTitle>
        <CardDescription>
          Get started with your data-driven Cultural Compatibility Score.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {error && <p className="mb-4 text-center text-sm text-destructive">{error}</p>}
        <form onSubmit={handleRegister} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              type="email"
              placeholder="analyst@firm.com"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="password">Password</Label>
            <Input
              id="password"
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>
           <div className="space-y-2">
            <Label htmlFor="confirm-password">Confirm Password</Label>
            <Input
              id="confirm-password"
              type="password"
              required
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
            />
          </div>
          <Button type="submit" className="w-full">
            Sign Up
          </Button>
        </form>
        <div className="my-4 flex items-center">
          <div className="flex-grow border-t border-muted" />
          <span className="mx-4 text-xs text-muted-foreground">OR</span>
          <div className="flex-grow border-t border-muted" />
        </div>
        <div className="space-y-2">
          <Button variant="outline" className="w-full" asChild>
            <a href={googleAuthUrl}>
              <FaGoogle className="mr-2" /> Sign up with Google
            </a>
          </Button>
        </div>
      </CardContent>
      <CardFooter className="flex justify-center text-sm">
        <p className="text-muted-foreground">
          Already have an account?{" "}
          <Link href="/login" className="text-primary hover:underline font-medium">
            Log In
          </Link>
        </p>
      </CardFooter>
    </Card>
  );
}
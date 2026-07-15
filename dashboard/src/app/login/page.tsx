"use client";

import { useState } from "react";
import { signIn } from "next-auth/react";
import { GitBranch, Mail, Loader2, Hexagon } from "lucide-react";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState<string | null>(null);

  const handleGitHubLogin = async () => {
    setIsLoading("github");
    await signIn("github", { callbackUrl: "/dashboard" });
  };

  const handleCredentialsLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) return;
    setIsLoading("credentials");
    await signIn("credentials", {
      email,
      password,
      callbackUrl: "/dashboard",
    });
  };

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4 selection:bg-primary selection:text-primary-foreground">
      <div className="relative w-full max-w-md">
        {/* Logo */}
        <div className="flex flex-col items-center mb-8 animate-in fade-in slide-in-from-bottom-4 duration-1000">
          <div className="w-12 h-12 bg-primary rounded-xl flex items-center justify-center mb-4 shadow-lg">
            <span className="text-primary-foreground font-bold text-xl">P</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tighter">ProjectFlow</h1>
          <p className="text-[10px] text-muted-foreground font-mono tracking-widest mt-1 uppercase">
            Project Management Platform
          </p>
        </div>

        {/* Card */}
        <div className="border border-border bg-card p-8 rounded-2xl shadow-xl animate-in fade-in zoom-in-95 duration-500">
          <div className="space-y-6">
            <div className="space-y-2 text-center mb-8">
              <h2 className="text-xl font-semibold tracking-tight">Welcome Back</h2>
              <p className="text-sm text-muted-foreground">Sign in to access your workspace</p>
            </div>

            {/* GitHub Button */}
            <button
              onClick={handleGitHubLogin}
              disabled={!!isLoading}
              className="w-full h-12 flex items-center justify-center gap-3 bg-primary text-primary-foreground hover:bg-primary/90 transition-all rounded-lg font-medium group disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading === "github" ? (
                <Loader2 className="animate-spin" size={20} />
              ) : (
                <GitBranch size={20} className="group-hover:scale-110 transition-transform" />
              )}
              <span>Continue with GitHub</span>
            </button>

            {/* Divider */}
            <div className="relative flex items-center py-2">
              <div className="flex-grow border-t border-border"></div>
              <span className="flex-shrink mx-4 text-[10px] text-muted-foreground font-mono uppercase tracking-widest">
                Or with Email
              </span>
              <div className="flex-grow border-t border-border"></div>
            </div>

            {/* Credentials Form */}
            <form onSubmit={handleCredentialsLogin} className="space-y-4">
              <div className="space-y-2">
                <div className="relative group">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground group-focus-within:text-foreground transition-colors" size={18} />
                  <input
                    type="email"
                    placeholder="name@company.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full h-11 bg-background border border-border pl-10 pr-4 rounded-lg focus:outline-none focus:ring-2 focus:ring-ring transition-all placeholder:text-muted-foreground text-sm"
                    required
                  />
                </div>
              </div>
              <div className="space-y-2">
                <input
                  type="password"
                  placeholder="Password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full h-11 bg-background border border-border px-4 rounded-lg focus:outline-none focus:ring-2 focus:ring-ring transition-all placeholder:text-muted-foreground text-sm"
                  required
                />
              </div>
              <button
                type="submit"
                disabled={!!isLoading}
                className="w-full h-11 flex items-center justify-center bg-secondary text-secondary-foreground border border-border hover:bg-muted transition-all rounded-lg font-medium disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isLoading === "credentials" ? (
                  <Loader2 className="animate-spin" size={20} />
                ) : (
                  "Sign In"
                )}
              </button>
            </form>
          </div>
        </div>

        <p className="mt-8 text-center text-xs text-muted-foreground">
          ProjectFlow — Plan, track, and deliver
        </p>
      </div>
    </div>
  );
}

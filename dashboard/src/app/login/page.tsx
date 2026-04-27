"use client";

import { useState } from "react";
import { signIn } from "next-auth/react";
import { GitBranch, Mail, Loader2, Hexagon } from "lucide-react";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [isLoading, setIsLoading] = useState<string | null>(null);

  const handleGitHubLogin = async () => {
    setIsLoading("github");
    await signIn("github", { callbackUrl: "/dashboard" });
  };

  const handleEmailLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) return;
    setIsLoading("email");
    await signIn("resend", { email, callbackUrl: "/dashboard" });
  };

  return (
    <div className="min-h-screen bg-black flex items-center justify-center p-4 selection:bg-white selection:text-black">
      {/* Background Decor */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-zinc-900/20 blur-[120px] rounded-full" />
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-zinc-900/20 blur-[120px] rounded-full" />
      </div>

      <div className="relative w-full max-w-md">
        {/* Logo */}
        <div className="flex flex-col items-center mb-8 animate-in fade-in slide-in-from-bottom-4 duration-1000">
          <div className="w-12 h-12 bg-white rounded-xl flex items-center justify-center mb-4 shadow-[0_0_40px_rgba(255,255,255,0.1)]">
            <Hexagon className="text-black fill-black" size={24} />
          </div>
          <h1 className="text-2xl font-bold tracking-tighter text-white uppercase">NexusBase</h1>
          <p className="text-[10px] text-zinc-500 font-mono tracking-widest mt-1 uppercase">Mission: Access Control</p>
        </div>

        {/* Modal */}
        <div className="bg-zinc-950 border border-zinc-800 p-8 rounded-2xl shadow-2xl animate-in fade-in zoom-in-95 duration-500">
          <div className="space-y-6">
            <div className="space-y-2 text-center mb-8">
              <h2 className="text-xl font-semibold text-white tracking-tight">Welcome Back</h2>
              <p className="text-sm text-zinc-500">Sign in to access your enterprise RAG dashboard</p>
            </div>

            {/* GitHub Button */}
            <button
              onClick={handleGitHubLogin}
              disabled={!!isLoading}
              className="w-full h-12 flex items-center justify-center gap-3 bg-white text-black hover:bg-zinc-200 transition-all rounded-lg font-medium group disabled:opacity-50 disabled:cursor-not-allowed"
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
              <div className="flex-grow border-t border-zinc-800"></div>
              <span className="flex-shrink mx-4 text-[10px] text-zinc-600 font-mono uppercase tracking-widest">Or via Magic Link</span>
              <div className="flex-grow border-t border-zinc-800"></div>
            </div>

            {/* Email Form */}
            <form onSubmit={handleEmailLogin} className="space-y-4">
              <div className="relative group">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500 group-focus-within:text-white transition-colors" size={18} />
                <input
                  type="email"
                  placeholder="name@company.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full h-12 bg-zinc-900 border border-zinc-800 text-white pl-10 pr-4 rounded-lg focus:outline-none focus:border-white transition-all placeholder:text-zinc-600 text-sm"
                  required
                />
              </div>
              <button
                type="submit"
                disabled={!!isLoading}
                className="w-full h-12 flex items-center justify-center bg-zinc-900 border border-zinc-800 text-white hover:bg-white hover:text-black transition-all rounded-lg font-medium disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isLoading === "email" ? (
                  <Loader2 className="animate-spin" size={20} />
                ) : (
                  "Send Magic Link"
                )}
              </button>
            </form>
          </div>
        </div>

        {/* Footer */}
        <p className="mt-8 text-center text-xs text-zinc-600 font-mono tracking-wider uppercase">
          Authorized Personnel Only
        </p>
      </div>
    </div>
  );
}

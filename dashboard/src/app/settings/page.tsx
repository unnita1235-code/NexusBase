"use client";

import { useState, useEffect } from "react";
import { ChevronLeft, Save, Shield, Sliders, Type, Lock, Eye, EyeOff, Loader2 } from "lucide-react";
import Link from "next/link";
import { getSettings, updateSettings } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import { Textarea } from "@/components/ui/textarea";

export default function SettingsPage() {
  const [settings, setSettings] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [showKeys, setShowKeys] = useState<Record<string, boolean>>({});

  useEffect(() => {
    fetchSettings();
  }, []);

  async function fetchSettings() {
    try {
      const data = await getSettings();
      setSettings(data.settings);
    } catch (error) {
      console.error("Failed to fetch settings:", error);
    } finally {
      setIsLoading(false);
    }
  }

  const handleSave = async () => {
    setIsSaving(true);
    try {
      await updateSettings(settings);
      // Refresh to get updated timestamps and masked values
      await fetchSettings();
    } catch (error) {
      console.error("Failed to save settings:", error);
    } finally {
      setIsSaving(false);
    }
  };

  const updateSetting = (key: string, value: any) => {
    setSettings(prev => prev.map(s => s.key === key ? { ...s, value: value.toString() } : s));
  };

  const getSetting = (key: string) => settings.find(s => s.key === key)?.value || "";

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-black text-white">
        <Loader2 className="animate-spin text-zinc-500" size={32} />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-black text-white p-8 max-w-[1000px] mx-auto pb-24">
      {/* ── Header ──────────────────────────────────────── */}
      <header className="mb-12 flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Link href="/dashboard" className="p-2 hover:bg-zinc-900 rounded-full transition-all text-zinc-400 hover:text-white">
            <ChevronLeft size={24} />
          </Link>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">System Settings</h1>
            <p className="text-xs text-muted-foreground uppercase tracking-widest mt-0.5">NexusBase Configuration Layer</p>
          </div>
        </div>
        <Button 
          onClick={handleSave} 
          disabled={isSaving}
          className="bg-white text-black hover:bg-zinc-200 font-bold px-6 border-none"
        >
          {isSaving ? <Loader2 className="animate-spin mr-2" size={16} /> : <Save className="mr-2" size={16} />}
          Save Changes
        </Button>
      </header>

      <div className="grid gap-8">
        {/* ── Prompt Registry ────────────────────────────── */}
        <section className="space-y-4">
          <div className="flex items-center gap-2 text-zinc-400 mb-2">
            <Type size={18} />
            <h2 className="text-sm font-bold uppercase tracking-widest">Prompt Registry</h2>
          </div>
          
          <Card className="bg-black border-zinc-800">
            <CardHeader>
              <CardTitle className="text-lg">Core Instruction Sets</CardTitle>
              <CardDescription className="text-zinc-500">Edit the base personas for document generation and relevance grading.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-3">
                <Label htmlFor="system_prompt" className="text-zinc-300">System Prompt</Label>
                <Textarea 
                  id="system_prompt"
                  value={getSetting("system_prompt")}
                  onChange={(e) => updateSetting("system_prompt", e.target.value)}
                  className="min-h-[120px] font-mono text-xs leading-relaxed"
                  placeholder="Define the LLM persona..."
                />
              </div>
              <div className="space-y-3">
                <Label htmlFor="grader_prompt" className="text-zinc-300">Grader Prompt</Label>
                <Textarea 
                  id="grader_prompt"
                  value={getSetting("grader_prompt")}
                  onChange={(e) => updateSetting("grader_prompt", e.target.value)}
                  className="min-h-[120px] font-mono text-xs leading-relaxed"
                  placeholder="Define the grading logic..."
                />
              </div>
            </CardContent>
          </Card>
        </section>

        {/* ── Vector Tuning ──────────────────────────────── */}
        <section className="space-y-4">
          <div className="flex items-center gap-2 text-zinc-400 mb-2">
            <Sliders size={18} />
            <h2 className="text-sm font-bold uppercase tracking-widest">Vector Tuning</h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Card className="bg-black border-zinc-800">
              <CardHeader>
                <CardTitle className="text-sm">Chunk Size</CardTitle>
                <CardDescription className="text-zinc-500">Maximum characters per document chunk.</CardDescription>
              </CardHeader>
              <CardContent className="pt-0">
                <div className="flex items-center gap-4">
                  <Slider 
                    value={[parseInt(getSetting("chunk_size") || "512")]}
                    min={256}
                    max={1024}
                    step={32}
                    onValueChange={(val) => updateSetting("chunk_size", val[0])}
                    className="flex-1"
                  />
                  <span className="text-sm font-mono bg-zinc-900 px-2 py-1 rounded w-16 text-center">
                    {getSetting("chunk_size")}
                  </span>
                </div>
              </CardContent>
            </Card>

            <Card className="bg-black border-zinc-800">
              <CardHeader>
                <CardTitle className="text-sm">Chunk Overlap</CardTitle>
                <CardDescription className="text-zinc-500">Overlap between adjacent chunks to preserve context.</CardDescription>
              </CardHeader>
              <CardContent className="pt-0">
                <div className="flex items-center gap-4">
                  <Slider 
                    value={[parseInt(getSetting("chunk_overlap") || "64")]}
                    min={0}
                    max={256}
                    step={8}
                    onValueChange={(val) => updateSetting("chunk_overlap", val[0])}
                    className="flex-1"
                  />
                  <span className="text-sm font-mono bg-zinc-900 px-2 py-1 rounded w-16 text-center">
                    {getSetting("chunk_overlap")}
                  </span>
                </div>
              </CardContent>
            </Card>
          </div>
        </section>

        {/* ── API Keys ──────────────────────────────────── */}
        <section className="space-y-4">
          <div className="flex items-center gap-2 text-zinc-400 mb-2">
            <Shield size={18} />
            <h2 className="text-sm font-bold uppercase tracking-widest">Security & API Keys</h2>
          </div>

          <Card className="bg-black border-zinc-800">
            <CardHeader>
              <CardTitle className="text-lg">Service Integration</CardTitle>
              <CardDescription className="text-zinc-500">API keys are AES-encrypted before being stored in the database.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {[
                { key: "openai_api_key", label: "OpenAI API Key" },
                { key: "anthropic_api_key", label: "Anthropic API Key" },
                { key: "gemini_api_key", label: "Gemini API Key" },
                { key: "vector_db_api_key", label: "Vector DB API Key" },
              ].map(({ key, label }) => (
                <div key={key} className="space-y-3">
                  <Label htmlFor={key} className="text-zinc-300">{label}</Label>
                  <div className="relative">
                    <Input 
                      id={key}
                      type={showKeys[key] ? "text" : "password"}
                      value={getSetting(key)}
                      onChange={(e) => updateSetting(key, e.target.value)}
                      className="pr-10 font-mono text-xs"
                      placeholder={getSetting(key) ? "••••••••••••••••" : `Enter ${label}`}
                    />
                    <button 
                      type="button"
                      onClick={() => setShowKeys(prev => ({ ...prev, [key]: !prev[key] }))}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-white transition-colors"
                    >
                      {showKeys[key] ? <EyeOff size={16} /> : <Eye size={16} />}
                    </button>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        </section>
      </div>

      {/* ── Footer Info ────────────────────────────────── */}
      <footer className="mt-12 pt-8 border-t border-zinc-900 flex justify-between items-center text-[10px] text-zinc-500 uppercase tracking-widest">
        <div>NexusBase v0.2.0 • Dynamic Config Layer Active</div>
        <div className="flex items-center gap-4">
          <span className="flex items-center gap-1">
            <Lock size={10} />
            Encrypted Storage
          </span>
          <span>Last Updated: {settings[0]?.updated_at ? new Date(settings[0].updated_at).toLocaleString() : "Never"}</span>
        </div>
      </footer>
    </div>
  );
}

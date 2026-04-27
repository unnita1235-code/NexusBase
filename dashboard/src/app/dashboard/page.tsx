"use client";

import { useState } from "react";
import type { AccessLevel, QueryResponse } from "@/lib/types";
import { queryRAG } from "@/lib/api";
import QueryPanel from "@/components/QueryPanel";
import GraphVisualizer from "@/components/GraphVisualizer";
import ChunkGrid from "@/components/ChunkGrid";
import { TokenBurnChart } from "@/components/TokenBurnChart";
import { IngestionFeed } from "@/components/IngestionFeed";
import TraceDrawer from "@/components/TraceDrawer";
import Link from "next/link";
import { Activity, Bookmark, LogOut, Settings } from "lucide-react";
import { signOut, useSession } from "next-auth/react";

export default function Dashboard() {
  const { data: session } = useSession();
  const [query, setQuery] = useState("");
  const [accessLevel, setAccessLevel] = useState<AccessLevel>("internal");
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<QueryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isTraceOpen, setIsTraceOpen] = useState(false);

  const handleSearch = async () => {
    if (!query.trim()) return;

    setIsLoading(true);
    setError(null);

    try {
      const response = await queryRAG(query, accessLevel);
      setResult(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : "An unexpected error occurred");
      setResult(null);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background text-foreground p-8 max-w-[1400px] mx-auto">
      {/* ── Header ──────────────────────────────────────── */}
      <header className="mb-12 flex items-center space-x-3">
        <div className="w-8 h-8 flex items-center justify-center bg-white text-black font-bold rounded-sm shadow-sm">
          ⬡
        </div>
        <div>
          <h1 className="text-2xl font-bold tracking-tight">NexusBase</h1>
          <p className="text-xs text-muted-foreground uppercase tracking-widest mt-0.5">
            Enterprise RAG • {session?.user?.role || "User"} Mode
          </p>
        </div>
        <div className="flex-1 flex justify-end gap-4 items-center">
          <Link 
            href="/settings" 
            className="p-2 hover:bg-zinc-800 rounded-full transition-colors text-zinc-400 hover:text-white"
          >
            <Settings size={20} />
          </Link>
          <button 
            onClick={() => signOut()}
            className="p-2 hover:bg-zinc-800 rounded-full transition-colors text-zinc-400 hover:text-white"
          >
            <LogOut size={20} />
          </button>
          <Link 
            href="/research" 
            className="flex items-center gap-2 px-4 py-2 bg-zinc-900 hover:bg-white hover:text-black border border-zinc-800 rounded-sm transition-all group"
          >
            <Bookmark size={14} className="text-zinc-500 group-hover:text-black" />
            <span className="text-[10px] font-bold uppercase tracking-widest">Research Mode</span>
          </Link>
        </div>
      </header>

      {/* ── Query Panel ─────────────────────────────────── */}
      <QueryPanel
        query={query}
        setQuery={setQuery}
        accessLevel={accessLevel}
        setAccessLevel={setAccessLevel}
        onSubmit={handleSearch}
        isLoading={isLoading}
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* ── Left Column: Retrieval Visualizer ───────────── */}
        <div className="lg:col-span-2 space-y-8">
          
          {/* Loading / Error States */}
          {isLoading && (
            <div className="flex flex-col items-center justify-center py-20 border border-border rounded-lg bg-card shadow-sm">
              <div className="w-8 h-8 border-2 border-border border-t-muted-foreground rounded-full animate-spin mb-4" />
              <div className="text-sm text-muted-foreground tracking-widest uppercase">
                Running self-corrective pipeline…
              </div>
            </div>
          )}

          {error && (
            <div className="p-6 border border-red-900/50 bg-red-950/20 rounded-lg">
              <div className="text-xs font-bold uppercase tracking-wider text-red-500 mb-2">⚠ Error</div>
              <div className="text-sm text-red-400/90">{error}</div>
            </div>
          )}

          {/* Results Area */}
          {result && !isLoading && (
            <>
              {result.graph_path.length > 0 && (
                <GraphVisualizer
                  graphPath={result.graph_path}
                  relevanceRatio={result.relevance_ratio}
                  rewrittenQuery={result.rewritten_query}
                  queryType={result.query_type}
                  graphEntities={result.graph_entities}
                  graphTraversalPath={result.graph_traversal_path}
                />
              )}

              <div className="p-8 border border-border bg-card rounded-lg shadow-sm">
                <div className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground mb-4 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-white animate-pulse" />
                    Generated Answer
                  </div>
                  <button 
                    onClick={() => setIsTraceOpen(true)}
                    className="flex items-center gap-2 px-3 py-1 bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 rounded-full transition-all group"
                  >
                    <Activity size={12} className="text-zinc-500 group-hover:text-white transition-colors" />
                    <span className="text-[10px] text-zinc-400 group-hover:text-white transition-colors">View Trace</span>
                  </button>
                </div>
                <div className="text-sm leading-relaxed text-foreground">
                  {result.answer}
                </div>
              </div>

              <ChunkGrid chunks={result.chunks} />
            </>
          )}

          {/* Empty State */}
          {!result && !isLoading && !error && (
            <div className="flex flex-col items-center justify-center py-24 border border-border border-dashed rounded-lg bg-black/50">
              <div className="text-4xl text-muted-foreground opacity-20 mb-4">⬡</div>
              <div className="text-sm font-medium text-muted-foreground mb-1">Ready to query</div>
              <div className="text-xs text-muted-foreground/60">Enter a question above to search your document store</div>
            </div>
          )}
        </div>

        {/* ── Right Column: Telemetry & Ingestion ─────────── */}
        <div className="space-y-8 lg:col-span-1">
          <div className="h-[280px]">
            <TokenBurnChart />
          </div>
          <div className="h-[400px]">
            <IngestionFeed />
          </div>
        </div>
      </div>

      {result && (
        <TraceDrawer 
          isOpen={isTraceOpen} 
          onClose={() => setIsTraceOpen(false)} 
          result={result} 
        />
      )}
    </div>
  );
}

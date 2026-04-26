"use client";

import { X, Search, GitBranch, Database, CheckCircle2 } from "lucide-react";
import { QueryResponse } from "@/lib/types";

interface TraceDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  result: QueryResponse;
}

export default function TraceDrawer({ isOpen, onClose, result }: TraceDrawerProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-black/60 backdrop-blur-sm animate-in fade-in duration-300" 
        onClick={onClose} 
      />
      
      {/* Drawer */}
      <div className="relative w-full max-w-md bg-zinc-950 border-l border-white/10 h-full shadow-2xl flex flex-col animate-in slide-in-from-right duration-500">
        <div className="p-6 border-b border-white/5 flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold tracking-tight text-white">Execution Trace</h2>
            <p className="text-[10px] uppercase tracking-widest text-zinc-500 mt-1">LangGraph Path Analysis</p>
          </div>
          <button 
            onClick={onClose}
            className="p-2 hover:bg-white/5 rounded-full transition-colors text-zinc-400 hover:text-white"
          >
            <X size={20} />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-8">
          <div className="relative space-y-12">
            {/* Timeline Vertical Line */}
            <div className="absolute left-4 top-2 bottom-2 w-px bg-zinc-800" />

            {/* Step: Query Rewrite */}
            <div className="relative pl-12 group">
              <div className="absolute left-2.5 top-1.5 w-3 h-3 rounded-full bg-zinc-900 border border-zinc-700 group-hover:border-zinc-400 transition-all shadow-[0_0_8px_rgba(255,255,255,0.1)]" />
              <div className="flex items-center gap-3 mb-2 text-zinc-400">
                <Search size={14} />
                <span className="text-xs font-bold uppercase tracking-widest">Query Rewritten</span>
              </div>
              <div className="bg-zinc-900/30 border border-zinc-800/50 p-4 rounded text-sm text-zinc-300 font-mono italic">
                {result.rewritten_query || "No rewrite needed (original query used)"}
              </div>
            </div>

            {/* Step: Router Decision */}
            <div className="relative pl-12 group">
              <div className="absolute left-2.5 top-1.5 w-3 h-3 rounded-full bg-zinc-900 border border-zinc-700 group-hover:border-zinc-400 transition-all shadow-[0_0_8px_rgba(255,255,255,0.1)]" />
              <div className="flex items-center gap-3 mb-2 text-zinc-400">
                <GitBranch size={14} />
                <span className="text-xs font-bold uppercase tracking-widest">Router Decision</span>
              </div>
              <div className="text-sm text-zinc-200">
                Path: <span className="text-white font-semibold">{result.query_type === "multi_hop" ? "GraphRAG (Traversal)" : "Standard RAG (Document)"}</span>
              </div>
            </div>

            {/* Step: DB Retrieval */}
            <div className="relative pl-12 group">
              <div className="absolute left-2.5 top-1.5 w-3 h-3 rounded-full bg-zinc-900 border border-zinc-700 group-hover:border-zinc-400 transition-all shadow-[0_0_8px_rgba(255,255,255,0.1)]" />
              <div className="flex items-center gap-3 mb-2 text-zinc-400">
                <Database size={14} />
                <span className="text-xs font-bold uppercase tracking-widest">DB Retrieval</span>
              </div>
              <div className="text-sm text-zinc-200">
                Fetched <span className="text-white font-semibold">{result.chunks.length}</span> chunks in <span className="text-white font-semibold">{result.retrieval_time_ms}ms</span>
              </div>
            </div>

            {/* Step: Grader Evaluation */}
            <div className="relative pl-12 group">
              <div className="absolute left-2.5 top-1.5 w-3 h-3 rounded-full bg-zinc-900 border border-zinc-700 group-hover:border-zinc-400 transition-all shadow-[0_0_8px_rgba(255,255,255,0.1)]" />
              <div className="flex items-center gap-3 mb-2 text-zinc-400">
                <CheckCircle2 size={14} />
                <span className="text-xs font-bold uppercase tracking-widest">Grader Evaluation</span>
              </div>
              <div className="flex gap-6">
                <div className="flex flex-col">
                  <span className="text-[10px] text-zinc-500 uppercase tracking-tighter mb-1">Passed Chunks</span>
                  <span className="text-green-400 font-mono font-bold text-lg">{result.total_relevant}</span>
                </div>
                <div className="flex flex-col">
                  <span className="text-[10px] text-zinc-500 uppercase tracking-tighter mb-1">Failed Chunks</span>
                  <span className="text-red-400 font-mono font-bold text-lg">{Math.max(0, result.total_graded - result.total_relevant)}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="p-6 border-t border-white/5 bg-black/40">
          <div className="flex flex-col gap-2">
            <span className="text-[10px] text-zinc-500 uppercase tracking-widest">Execution Path</span>
            <div className="flex flex-wrap gap-2">
              {result.graph_path.map((node, idx) => (
                <div key={idx} className="flex items-center gap-2">
                  <span className="px-2 py-1 bg-zinc-900 border border-zinc-800 rounded text-[10px] text-zinc-300 font-mono">
                    {node}
                  </span>
                  {idx < result.graph_path.length - 1 && <span className="text-zinc-700">→</span>}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

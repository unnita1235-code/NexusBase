"use client";

import type { RetrievedChunk } from "@/lib/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";

interface ChunkGridProps {
  chunks: RetrievedChunk[];
}

export default function ChunkGrid({ chunks }: ChunkGridProps) {
  if (chunks.length === 0) {
    return (
      <Card className="rounded-sm border-border bg-black h-full flex items-center justify-center min-h-[300px]">
        <div className="text-center">
          <div className="text-3xl mb-2 text-muted-foreground opacity-50">◇</div>
          <div className="text-sm font-medium text-muted-foreground">No chunks retrieved</div>
        </div>
      </Card>
    );
  }

  return (
    <Card className="rounded-sm border-border bg-black h-full flex flex-col">
      <CardHeader>
        <CardTitle className="text-sm font-medium tracking-wide uppercase text-muted-foreground flex justify-between items-center">
          <span>Retrieval Visualizer (Top 5 Chunks)</span>
          <span className="font-mono text-xs">{chunks.length} Results</span>
        </CardTitle>
      </CardHeader>
      <CardContent className="flex-1 overflow-y-auto pr-2 space-y-4">
        {chunks.map((chunk) => (
          <div key={chunk.chunk_id} className="p-4 border border-border rounded-sm bg-[#080808] transition-colors hover:border-[#333]">
            <div className="flex items-center justify-between mb-3 border-b border-border pb-2">
              <span className="font-mono text-xs font-bold text-white">#{chunk.rank}</span>
              <span className="font-mono text-[10px] text-muted-foreground truncate max-w-[200px]" title={chunk.source}>
                {chunk.source} {chunk.page !== null ? `(p.${chunk.page})` : ""}
              </span>
              <span className="px-2 py-0.5 border border-border rounded-full text-[9px] uppercase tracking-wider text-muted-foreground">
                {chunk.access_level}
              </span>
            </div>
            
            <p className="text-xs leading-relaxed text-[#aaa] line-clamp-3 mb-4">
              {chunk.content}
            </p>

            <div className="space-y-2">
              <div className="flex items-center justify-between text-[10px] font-mono uppercase text-[#777]">
                <span>Cosine Similarity</span>
                <span className="text-white">{(chunk.distance_score * 100).toFixed(1)}%</span>
              </div>
              <Progress value={Math.min(chunk.distance_score * 100, 100)} className="h-1 bg-[#111] [&>div]:bg-white" />
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

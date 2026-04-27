"use client";

import type { RetrievedChunk } from "@/lib/types";
import { Globe } from "lucide-react";
import StatusBadge from "./StatusBadge";
import ScoreBar from "./ScoreBar";

interface ChunkCardProps {
  chunk: RetrievedChunk;
}

export default function ChunkCard({ chunk }: ChunkCardProps) {
  return (
    <div className="chunk-card">
      {/* Header: Rank + Source */}
      <div className="chunk-card__header">
        <span className="chunk-card__rank">#{chunk.rank}</span>
        <div className="flex items-center gap-1.5 overflow-hidden">
          {chunk.is_external && (
            <Globe size={12} className="text-zinc-400 flex-shrink-0" />
          )}
          <span className="chunk-card__source truncate" title={chunk.source}>
            {chunk.source}
          </span>
        </div>
      </div>

      {/* Content snippet */}
      <p className="chunk-card__content">{chunk.content}</p>

      {/* Score bars */}
      <div className="chunk-card__scores">
        <ScoreBar
          label="Weighted"
          value={chunk.weighted_score}
          maxValue={1}
        />
        <ScoreBar
          label="Distance"
          value={chunk.distance_score}
          maxValue={2}
        />
        <ScoreBar
          label="RRF"
          value={chunk.rrf_score}
          maxValue={0.05}
        />
      </div>

      {/* Footer: Access badge + page */}
      <div className="chunk-card__footer">
        <StatusBadge level={chunk.access_level} />
        {chunk.page !== null && (
          <span className="chunk-card__page">Page {chunk.page}</span>
        )}
      </div>
    </div>
  );
}

"use client";

interface GraphVisualizerProps {
  graphPath: string[];
  relevanceRatio?: number;
  rewrittenQuery?: string | null;
  queryType?: "simple" | "multi_hop";
  graphEntities?: string[];
  graphTraversalPath?: string[];
}

const NODE_LABELS: Record<string, string> = {
  retrieve: "Retrieve",
  grade_documents: "Grade",
  generate: "Generate",
  web_search: "Web Search",
  query_rewrite: "Rewrite",
  secondary_search: "Secondary",
};

export default function GraphVisualizer({
  graphPath,
  relevanceRatio,
  rewrittenQuery,
  queryType,
  graphEntities,
  graphTraversalPath,
}: GraphVisualizerProps) {
  // Deduplicate path for display
  const seen = new Set<string>();
  const displayPath: string[] = [];
  for (const node of graphPath) {
    if (!seen.has(node)) {
      seen.add(node);
      displayPath.push(node);
    }
  }

  const isMultiHop = queryType === "multi_hop";

  return (
    <div className="bg-card border border-border rounded-lg p-6 mb-8 shadow-sm">
      {/* Title bar */}
      <div className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-6 flex items-center">
        {isMultiHop ? "GraphRAG Pipeline" : "CRAG Pipeline Flow"}
        {relevanceRatio !== undefined && (
          <span className={`ml-3 font-mono text-[10px] px-2 py-0.5 rounded-sm border ${relevanceRatio > 0 ? "border-foreground text-foreground bg-foreground/10" : "border-border text-muted-foreground"}`}>
            REL: {(relevanceRatio * 100).toFixed(0)}%
          </span>
        )}
        {isMultiHop && (
          <span className="ml-2 font-mono text-[10px] px-2 py-0.5 rounded-sm border border-border text-foreground bg-[#111]">
            MULTI-HOP
          </span>
        )}
      </div>

      {/* Pipeline flow */}
      <div className="flex flex-wrap items-center">
        {displayPath.map((node, index) => {
          const isActive = graphPath.includes(node);
          const isLast = index === displayPath.length - 1;

          return (
            <div key={`${node}-${index}`} className="flex items-center">
              <div
                className={`flex items-center justify-center px-4 py-2 text-xs font-mono border rounded-sm transition-colors ${
                  isActive 
                    ? "bg-[#111] border-foreground text-foreground shadow-[0_0_10px_rgba(255,255,255,0.1)]" 
                    : "bg-background border-border text-muted-foreground"
                }`}
              >
                {NODE_LABELS[node] || node}
              </div>
              {!isLast && (
                <div className="flex items-center w-8">
                  <div className={`h-[1px] w-full ${isActive ? "bg-foreground" : "bg-border"}`} />
                  <div className={`w-0 h-0 border-y-4 border-y-transparent border-l-[6px] -ml-[2px] ${isActive ? "border-l-foreground" : "border-l-border"}`} />
                </div>
              )}
            </div>
          );
        })}
        <div className="flex items-center w-8">
          <div className="h-[1px] w-full bg-foreground" />
          <div className="w-0 h-0 border-y-4 border-y-transparent border-l-[6px] -ml-[2px] border-l-foreground" />
        </div>
        <div className="flex items-center justify-center w-8 h-8 rounded-full border border-foreground bg-[#111] text-foreground text-[10px] font-bold">
          END
        </div>
      </div>

      {/* Graph entities (multi-hop only) */}
      {isMultiHop && graphEntities && graphEntities.length > 0 && (
        <div className="mt-6 p-4 bg-background border border-border rounded-sm">
          <div className="text-[10px] font-bold uppercase tracking-widest text-foreground mb-3">
            ⬡ Knowledge Graph Entities
          </div>
          <div className="flex flex-wrap gap-2">
            {graphEntities.map((entity) => (
              <span key={entity} className="px-2.5 py-1 rounded-sm bg-[#111] text-foreground text-xs font-mono border border-border">
                {entity}
              </span>
            ))}
          </div>

          {/* Traversal path */}
          {graphTraversalPath && graphTraversalPath.length > 0 && (
            <div className="mt-4 text-[10px] text-muted-foreground font-mono leading-relaxed p-3 bg-[#0a0a0a] border border-border rounded-sm">
              <span className="text-foreground font-bold">TRAVERSAL: </span>
              {graphTraversalPath.join(" ")}
            </div>
          )}
        </div>
      )}

      {/* Rewritten query indicator */}
      {rewrittenQuery && (
        <div className="mt-4 p-3 bg-background border border-border rounded-sm text-xs text-muted-foreground font-mono">
          <span className="text-foreground font-bold mr-2">↻ REWRITTEN:</span>
          &quot;{rewrittenQuery}&quot;
        </div>
      )}
    </div>
  );
}

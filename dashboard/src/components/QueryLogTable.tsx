"use client"

import { useState } from "react"
import { 
  Table, 
  TableBody, 
  TableCell, 
  TableHead, 
  TableHeader, 
  TableRow 
} from "@/components/ui/table"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { QueryResponse } from "@/lib/types"
import TraceDrawer from "@/components/TraceDrawer"
import { Eye } from "lucide-react"

// Mock data for the table
const mockQueries: (QueryResponse & { id: string; timestamp: string; query: string })[] = [
  {
    id: "1",
    timestamp: "2026-04-27 02:10:45",
    query: "What is the token burn rate for GPT-4o?",
    answer: "The token burn rate depends on usage...",
    chunks: [],
    graph_path: ["input", "router", "vector_db", "generator"],
    relevance_ratio: 0.95,
    rewritten_query: "GPT-4o token cost analysis",
    query_type: "simple",
    graph_entities: [],
    graph_traversal_path: [],
    total_graded: 5,
    total_relevant: 5,
    retrieval_time_ms: 124,
  },
  {
    id: "2",
    timestamp: "2026-04-27 01:55:12",
    query: "Compare RAG vs GraphRAG performance",
    answer: "GraphRAG typically performs better on multi-hop...",
    chunks: [],
    graph_path: ["input", "router", "graph_traversal", "generator"],
    relevance_ratio: 0.88,
    rewritten_query: "RAG and GraphRAG performance comparison",
    query_type: "multi_hop",
    graph_entities: ["RAG", "GraphRAG"],
    graph_traversal_path: ["Entity:RAG", "Entity:GraphRAG"],
    total_graded: 10,
    total_relevant: 8,
    retrieval_time_ms: 450,
  },
  {
    id: "3",
    timestamp: "2026-04-27 01:30:05",
    query: "Explain Cosine Similarity in vector search",
    answer: "Cosine similarity measures the cosine of the angle...",
    chunks: [],
    graph_path: ["input", "router", "vector_db", "generator"],
    relevance_ratio: 0.92,
    rewritten_query: "Vector search cosine similarity explanation",
    query_type: "simple",
    graph_entities: [],
    graph_traversal_path: [],
    total_graded: 3,
    total_relevant: 3,
    retrieval_time_ms: 89,
  }
]

export function QueryLogTable() {
  const [selectedTrace, setSelectedTrace] = useState<QueryResponse | null>(null)

  return (
    <div className="w-full space-y-4">
      <div className="rounded-none border-dotted border-2 border-zinc-800 bg-black overflow-hidden">
        <Table>
          <TableHeader className="bg-zinc-950/50">
            <TableRow className="border-zinc-800 hover:bg-transparent">
              <TableHead className="text-[10px] font-bold uppercase tracking-widest text-zinc-500 w-[150px]">Timestamp</TableHead>
              <TableHead className="text-[10px] font-bold uppercase tracking-widest text-zinc-500">Query</TableHead>
              <TableHead className="text-[10px] font-bold uppercase tracking-widest text-zinc-500">Type</TableHead>
              <TableHead className="text-[10px] font-bold uppercase tracking-widest text-zinc-500 text-right">Latency</TableHead>
              <TableHead className="text-[10px] font-bold uppercase tracking-widest text-zinc-500 text-right">Action</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {mockQueries.map((item) => (
              <TableRow key={item.id} className="border-zinc-800 hover:bg-zinc-900/30 transition-colors group">
                <TableCell className="font-mono text-[10px] text-zinc-400">{item.timestamp}</TableCell>
                <TableCell className="text-sm text-zinc-200 max-w-[300px] truncate">{item.query}</TableCell>
                <TableCell>
                  <span className={`text-[9px] uppercase font-bold tracking-tighter px-1.5 py-0.5 border ${
                    item.query_type === 'multi_hop' ? 'border-zinc-400 text-white' : 'border-zinc-800 text-zinc-500'
                  }`}>
                    {item.query_type}
                  </span>
                </TableCell>
                <TableCell className="text-right font-mono text-[10px] text-zinc-400">
                  {item.retrieval_time_ms}ms
                </TableCell>
                <TableCell className="text-right">
                  <Button 
                    variant="ghost" 
                    size="sm" 
                    className="h-7 px-2 text-[10px] uppercase font-bold tracking-widest hover:bg-white hover:text-black rounded-none border border-zinc-800"
                    onClick={() => setSelectedTrace(item)}
                  >
                    <Eye size={12} className="mr-1" />
                    Trace
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      {selectedTrace && (
        <TraceDrawer 
          isOpen={!!selectedTrace} 
          onClose={() => setSelectedTrace(null)} 
          result={selectedTrace} 
        />
      )}
    </div>
  )
}

"use client";

import { useState, useRef, useEffect } from "react";
import { Send, Terminal, Loader2, ShieldCheck, Globe } from "lucide-react";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: Array<{
    id: number;
    pdf_url: string;
    page: number;
    bounding_box: any;
    is_external?: boolean;
  }>;
}

interface ChatPanelProps {
  onCitationClick: (citation: any) => void;
}

export default function ChatPanel({ onCitationClick }: ChatPanelProps) {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "1",
      role: "assistant",
      content: "NEURAL LINK ESTABLISHED. I have analyzed the repository. Ask me any question to trace facts back to their source.",
    }
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage: Message = { id: Date.now().toString(), role: "user", content: input };
    setMessages(prev => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);

    // Mocking an intelligent response with citations to demonstrate the split-screen functionality
    setTimeout(() => {
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: "Based on the technical specification [1], the core architecture utilizes a self-corrective retrieval loop. Section 4.2 of the audit [2] confirms that this approach reduces hallucinations by 42% compared to standard RAG.",
        citations: [
          {
            id: 1,
            pdf_url: "https://pdfobject.com/pdf/sample.pdf", // Using a reliable sample PDF
            page: 1,
            bounding_box: { x: 15, y: 10, width: 70, height: 5 }
          },
          {
            id: 2,
            pdf_url: "https://pdfobject.com/pdf/sample.pdf",
            page: 2,
            bounding_box: { x: 20, y: 40, width: 60, height: 8 }
          }
        ]
      };
      setMessages(prev => [...prev, assistantMessage]);
      setIsLoading(false);
    }, 1200);
  };

  const renderContent = (content: string, citations?: any[]) => {
    if (!citations) return content;

    const parts = content.split(/(\[\d+\])/g);
    return parts.map((part, i) => {
      const match = part.match(/\[(\d+)\]/);
      if (match) {
        const id = parseInt(match[1]);
        const citation = citations.find(c => c.id === id);
        if (citation) {
          return (
            <button
              key={i}
              onClick={() => onCitationClick(citation)}
              className="inline-flex items-center justify-center w-5 h-5 mx-1 text-[9px] font-bold border border-zinc-800 bg-zinc-900 text-zinc-400 rounded-sm hover:bg-white hover:text-black hover:border-white transition-all cursor-pointer"
              title={citation.is_external ? `View Web Source: ${citation.pdf_url}` : `View Source Citation [${id}]`}
            >
              {citation.is_external ? <Globe size={10} /> : id}
            </button>
          );
        }
      }
      return <span key={i}>{part}</span>;
    });
  };

  return (
    <div className="flex flex-col h-full bg-black border-r border-zinc-900">
      {/* Header */}
      <div className="p-6 border-b border-zinc-900 flex items-center justify-between bg-zinc-950/20">
        <div className="flex items-center gap-3">
          <div className="w-2 h-2 rounded-full bg-white animate-pulse" />
          <h2 className="text-[10px] font-bold uppercase tracking-[0.3em] text-white">Trust_Layer.v1</h2>
        </div>
        <div className="flex items-center gap-2 px-3 py-1 rounded-full border border-zinc-800 bg-zinc-900/50">
          <ShieldCheck size={10} className="text-zinc-400" />
          <span className="text-[8px] text-zinc-400 uppercase font-bold tracking-widest">Evidence Sync: Active</span>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-8 space-y-10 custom-scrollbar">
        {messages.map((m) => (
          <div key={m.id} className={`flex flex-col ${m.role === 'user' ? 'items-end' : 'items-start'}`}>
            <div className={`max-w-[85%] p-5 rounded-none border ${
              m.role === 'user' 
                ? 'bg-zinc-900 border-zinc-800 text-zinc-100 shadow-[4px_4px_0px_rgba(255,255,255,0.05)]' 
                : 'bg-black border-zinc-900 text-zinc-400 shadow-[4px_4px_0px_rgba(0,0,0,1)]'
            }`}>
              <div className="text-[13px] leading-relaxed font-light tracking-wide">
                {renderContent(m.content, m.citations)}
              </div>
            </div>
            <div className="mt-3 text-[8px] uppercase tracking-[0.4em] text-zinc-700 font-bold">
              {m.role === 'user' ? '// OPERATOR' : '// NEXUS_NODE'}
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="flex items-center gap-4 py-4">
            <Loader2 size={12} className="animate-spin text-zinc-600" />
            <div className="text-[9px] uppercase tracking-[0.4em] text-zinc-600 italic">Scanning Document Store...</div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="p-8 border-t border-zinc-900 bg-zinc-950/30">
        <form onSubmit={handleSubmit} className="relative group">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="SUBMIT RESEARCH QUERY..."
            className="w-full bg-black border border-zinc-800 rounded-none px-6 py-5 text-xs font-mono tracking-widest focus:outline-none focus:border-white transition-all placeholder:text-zinc-800 text-white"
          />
          <button
            type="submit"
            disabled={!input.trim() || isLoading}
            className="absolute right-4 top-1/2 -translate-y-1/2 p-3 text-zinc-600 hover:text-white disabled:opacity-20 transition-colors"
          >
            <Send size={18} />
          </button>
          <div className="absolute -bottom-5 left-2 text-[7px] text-zinc-800 uppercase tracking-[0.5em] font-bold">
            System Status: Awaiting Command
          </div>
        </form>
      </div>
    </div>
  );
}

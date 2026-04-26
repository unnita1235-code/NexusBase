"use client";

import { useState } from "react";
import ChatPanel from "./ChatPanel";
import PdfViewerPanel from "./PdfViewerPanel";

export default function TrustSplitView() {
  const [activeCitation, setActiveCitation] = useState<any>(null);

  const handleCitationClick = (citation: any) => {
    // Reset and set to trigger effect even if it's the same citation
    setActiveCitation(null);
    setTimeout(() => {
        setActiveCitation(citation);
    }, 10);
  };

  return (
    <div className="flex h-screen w-full bg-black overflow-hidden selection:bg-zinc-800 selection:text-white">
      {/* Sidebar / Left Pane: Chat Interface */}
      <div className="w-[450px] flex-shrink-0 flex flex-col border-r border-zinc-900 z-10 shadow-[20px_0_50px_rgba(0,0,0,0.5)]">
        <ChatPanel onCitationClick={handleCitationClick} />
      </div>

      {/* Main / Right Pane: PDF Evidence Viewer */}
      <div className="flex-1 relative bg-[#050505]">
        <PdfViewerPanel
          pdfUrl={activeCitation?.pdf_url || null}
          pageNumber={activeCitation?.page || null}
          boundingBox={activeCitation?.bounding_box || null}
        />
        
        {/* Breadcrumb / Status Overlay */}
        {activeCitation && (
          <div className="absolute top-6 left-6 right-6 flex items-center justify-between pointer-events-none">
            <div className="px-4 py-2 bg-black/80 backdrop-blur-md border border-zinc-800 text-[10px] uppercase tracking-[0.2em] text-zinc-400 font-mono flex items-center gap-3">
              <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full shadow-[0_0_8px_#10b981]" />
              SOURCE_LINK: {activeCitation.pdf_url.split('/').pop()} // PAGE_{activeCitation.page}
            </div>
            
            <div className="px-4 py-2 bg-black/80 backdrop-blur-md border border-zinc-800 text-[10px] uppercase tracking-[0.2em] text-zinc-500 font-mono">
              COORDS: {activeCitation.bounding_box.x}, {activeCitation.bounding_box.y}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

"use client";

import { useState, useEffect, useRef } from "react";
import { Document, Page, pdfjs } from "react-pdf";
import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";

// Set up worker - using standard version from package
pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

interface PdfViewerPanelProps {
  pdfUrl: string | null;
  pageNumber: number | null;
  boundingBox: { x: number; y: number; width: number; height: number } | null;
}

export default function PdfViewerPanel({ pdfUrl, pageNumber, boundingBox }: PdfViewerPanelProps) {
  const [numPages, setNumPages] = useState<number>(0);
  const containerRef = useRef<HTMLDivElement>(null);
  const highlightRef = useRef<HTMLDivElement>(null);

  function onDocumentLoadSuccess({ numPages }: { numPages: number }) {
    setNumPages(numPages);
  }

  useEffect(() => {
    if (highlightRef.current) {
        highlightRef.current.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }, [pageNumber, boundingBox, pdfUrl]);

  if (!pdfUrl) {
    return (
      <div className="flex flex-col items-center justify-center h-full bg-black border-l border-zinc-900 text-zinc-700">
        <div className="text-[10px] font-bold uppercase tracking-[0.3em] mb-4">No Document Loaded</div>
        <div className="w-12 h-[1px] bg-zinc-900" />
      </div>
    );
  }

  return (
    <div ref={containerRef} className="h-full overflow-y-auto bg-black scroll-smooth custom-scrollbar">
      <div className="py-12 flex flex-col items-center">
        <Document
          file={pdfUrl}
          onLoadSuccess={onDocumentLoadSuccess}
          className="flex flex-col items-center gap-12"
          loading={
            <div className="flex flex-col items-center py-20">
               <div className="w-6 h-6 border-t-2 border-white rounded-full animate-spin mb-4" />
               <div className="text-[10px] uppercase tracking-widest text-zinc-500">Decrypting Source...</div>
            </div>
          }
        >
          {Array.from(new Array(numPages), (el, index) => (
            <div 
              key={`page_${index + 1}`} 
              className="relative shadow-[0_0_50px_rgba(0,0,0,0.5)] border border-zinc-900 transition-all duration-500 hover:border-zinc-800"
            >
              <Page
                pageNumber={index + 1}
                width={800}
                renderAnnotationLayer={false}
                renderTextLayer={true}
                className="bg-zinc-900"
              />
              {/* Highlight Overlay */}
              {pageNumber === index + 1 && boundingBox && (
                <div
                  ref={highlightRef}
                  style={{
                    position: "absolute",
                    left: `${boundingBox.x}%`,
                    top: `${boundingBox.y}%`,
                    width: `${boundingBox.width}%`,
                    height: `${boundingBox.height}%`,
                    backgroundColor: "#333333",
                    opacity: 0.6,
                    border: "1px solid rgba(255, 255, 255, 0.2)",
                    mixBlendMode: "screen",
                    pointerEvents: "none",
                    zIndex: 10,
                  }}
                  className="animate-pulse"
                />
              )}
              {/* Page Number Badge */}
              <div className="absolute -left-12 top-0 text-[10px] font-mono text-zinc-700">
                P.{index + 1}
              </div>
            </div>
          ))}
        </Document>
      </div>
    </div>
  );
}

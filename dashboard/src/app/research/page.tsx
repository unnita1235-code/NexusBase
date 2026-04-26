"use client";

import dynamic from "next/dynamic";

const TrustSplitView = dynamic(() => import("@/components/TrustSplitView"), {
  ssr: false,
});

export default function ResearchPage() {
  return (
    <main className="min-h-screen bg-black">
      <TrustSplitView />
    </main>
  );
}



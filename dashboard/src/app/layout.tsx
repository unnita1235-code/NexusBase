import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "NexusBase — RAG Dashboard",
  description:
    "Enterprise-grade RAG system dashboard. Visualize retrieved chunks, relevance scores, and the self-corrective retrieval graph.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

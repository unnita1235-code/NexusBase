"use client";

import { FormEvent } from "react";
import type { AccessLevel } from "@/lib/types";

interface QueryPanelProps {
  query: string;
  setQuery: (q: string) => void;
  accessLevel: AccessLevel;
  setAccessLevel: (level: AccessLevel) => void;
  onSubmit: () => void;
  isLoading: boolean;
}

export default function QueryPanel({
  query,
  setQuery,
  accessLevel,
  setAccessLevel,
  onSubmit,
  isLoading,
}: QueryPanelProps) {
  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (query.trim() && !isLoading) {
      onSubmit();
    }
  };

  return (
    <div className="bg-card border border-border rounded-lg p-6 mb-8 shadow-sm">
      <form className="flex flex-col md:flex-row gap-4 items-end" onSubmit={handleSubmit}>
        <div className="flex-1 flex flex-col gap-2 w-full">
          <label className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground" htmlFor="query-input">
            Query
          </label>
          <input
            id="query-input"
            className="bg-input border border-border rounded-md px-4 py-3 text-sm text-foreground focus:outline-none focus:border-ring transition-colors w-full"
            type="text"
            placeholder="Ask anything about your documents..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            disabled={isLoading}
            autoComplete="off"
          />
        </div>

        <div className="flex flex-col gap-2 md:w-48 w-full">
          <label className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground" htmlFor="access-level">
            Access Level
          </label>
          <select
            id="access-level"
            className="bg-input border border-border rounded-md px-4 py-3 text-sm text-foreground focus:outline-none focus:border-ring transition-colors w-full appearance-none cursor-pointer"
            value={accessLevel}
            onChange={(e) => setAccessLevel(e.target.value as AccessLevel)}
            disabled={isLoading}
          >
            <option value="public">Public</option>
            <option value="internal">Internal</option>
            <option value="confidential">Confidential</option>
            <option value="restricted">Restricted</option>
          </select>
        </div>

        <button
          type="submit"
          className="bg-foreground text-background font-semibold text-sm px-8 py-3 rounded-md hover:bg-neutral-300 transition-colors disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap"
          disabled={!query.trim() || isLoading}
        >
          {isLoading ? "Searching…" : "Search"}
        </button>
      </form>
    </div>
  );
}

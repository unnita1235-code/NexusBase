"use client";

import type { AccessLevel } from "@/lib/types";

interface StatusBadgeProps {
  level: AccessLevel;
}

const BADGE_CONFIG: Record<AccessLevel, { label: string; className: string }> = {
  public: { label: "Public", className: "status-badge--public" },
  internal: { label: "Internal", className: "status-badge--internal" },
  confidential: { label: "Confidential", className: "status-badge--confidential" },
  restricted: { label: "Restricted", className: "status-badge--restricted" },
};

export default function StatusBadge({ level }: StatusBadgeProps) {
  const config = BADGE_CONFIG[level] || BADGE_CONFIG.internal;

  return (
    <span className={`status-badge ${config.className}`}>
      <span className="status-badge__dot" />
      {config.label}
    </span>
  );
}

"use client";

interface ScoreBarProps {
  label: string;
  value: number;
  maxValue?: number;
}

export default function ScoreBar({ label, value, maxValue = 1 }: ScoreBarProps) {
  const percentage = Math.min((value / maxValue) * 100, 100);
  const displayValue = value < 0.001 ? value.toExponential(2) : value.toFixed(4);

  return (
    <div className="score-bar">
      <span className="score-bar__label">{label}</span>
      <div className="score-bar__track">
        <div
          className="score-bar__fill"
          style={{ width: `${percentage}%` }}
        />
      </div>
      <span className="score-bar__value">{displayValue}</span>
    </div>
  );
}

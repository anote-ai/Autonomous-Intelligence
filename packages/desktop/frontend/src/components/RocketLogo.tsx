import React from "react";
import { useTheme } from "../App";

export default function RocketLogo({ className = "w-8 h-8" }: { className?: string }) {
  const { dark } = useTheme();
  const body = dark ? "#FFFFFF" : "#111111";
  const accent = dark ? "#9CA3AF" : "#6B7280";
  const window_ = dark ? "#111111" : "#FFFFFF";
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M12 2C9 5.5 7 9 7 13c0 2.76 2.24 5 5 5s5-2.24 5-5c0-4-2-7.5-5-11z" fill={body} />
      <path d="M7 13c-1.5 0-3 1-3 3l2 2c.5-1 1.5-1.5 1-5z" fill={accent} />
      <path d="M17 13c1.5 0 3 1 3 3l-2 2c-.5-1-1.5-1.5-1-5z" fill={accent} />
      <path d="M10 18c0 2 1 3 2 4 1-1 2-2 2-4" fill={accent} />
      <circle cx="12" cy="12" r="2" fill={window_} stroke={accent} strokeWidth="0.5" />
    </svg>
  );
}

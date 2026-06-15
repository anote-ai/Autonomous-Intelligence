import { useTheme } from "../App";

interface Props {
  className?: string;
}

export default function RocketLogo({ className = "w-8 h-8" }: Props) {
  const { dark } = useTheme();

  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      {/* Rocket body */}
      <path
        d="M12 2C9 5.5 7 9 7 13c0 2.76 2.24 5 5 5s5-2.24 5-5c0-4-2-7.5-5-11z"
        fill={dark ? "#FFFFFF" : "#111111"}
      />
      {/* Rocket fins */}
      <path
        d="M7 13c-1.5 0-3 1-3 3l2 2c.5-1 1.5-1.5 1-5z"
        fill={dark ? "#9CA3AF" : "#6B7280"}
      />
      <path
        d="M17 13c1.5 0 3 1 3 3l-2 2c-.5-1-1.5-1.5-1-5z"
        fill={dark ? "#9CA3AF" : "#6B7280"}
      />
      {/* Flame */}
      <path
        d="M10 18c0 2 1 3 2 4 1-1 2-2 2-4"
        fill={dark ? "#9CA3AF" : "#6B7280"}
      />
      {/* Window */}
      <circle
        cx="12"
        cy="12"
        r="2"
        fill={dark ? "#111111" : "#FFFFFF"}
        stroke={dark ? "#9CA3AF" : "#6B7280"}
        strokeWidth="0.5"
      />
    </svg>
  );
}

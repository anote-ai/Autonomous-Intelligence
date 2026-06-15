import React from "react";
import Svg, { Path, Circle } from "react-native-svg";

interface Props {
  size?: number;
  bodyColor?: string;
  accentColor?: string;
}

export default function RocketLogo({ size = 32, bodyColor = "#111111", accentColor = "#6B7280" }: Props) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <Path
        d="M12 2C9 5.5 7 9 7 13c0 2.76 2.24 5 5 5s5-2.24 5-5c0-4-2-7.5-5-11z"
        fill={bodyColor}
      />
      <Path
        d="M7 13c-1.5 0-3 1-3 3l2 2c.5-1 1.5-1.5 1-5z"
        fill={accentColor}
      />
      <Path
        d="M17 13c1.5 0 3 1 3 3l-2 2c-.5-1-1.5-1.5-1-5z"
        fill={accentColor}
      />
      <Path d="M10 18c0 2 1 3 2 4 1-1 2-2 2-4" fill={accentColor} />
      <Circle cx="12" cy="12" r="2" fill={bodyColor === "#FFFFFF" ? "#111111" : "#FFFFFF"} />
    </Svg>
  );
}

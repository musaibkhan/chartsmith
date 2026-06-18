export const COLORS = {
  bg:       "#0E1116",
  panel:    "#161A22",
  panelHi:  "#1C2230",
  line:     "#262C3A",
  text:     "#E6E8EC",
  mute:     "#8A93A6",
  ember:    "#FF6B2C",
  emberSoft:"#FF6B2C22",
  mint:     "#3DDC97",
  amber:    "#FFC857",
  rose:     "#FF5C7A",
  violet:   "#A78BFA",
};

export const FONT_DISPLAY = `"Space Grotesk", ui-sans-serif, system-ui`;
export const FONT_BODY    = `"Inter", ui-sans-serif, system-ui`;
export const FONT_MONO    = `"JetBrains Mono", ui-monospace, SFMono-Regular, monospace`;

export const SEV_META: Record<string, { label: string; color: string }> = {
  critical: { label: "Critical", color: COLORS.rose  },
  high:     { label: "High",     color: COLORS.ember },
  medium:   { label: "Medium",   color: COLORS.amber },
  safe:     { label: "Safe",     color: COLORS.mint  },
};

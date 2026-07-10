// Reads design tokens from the CSS custom properties defined in index.css, so
// chart color values (which Chart.js needs as plain strings, not CSS vars) stay
// in sync with the theme instead of being duplicated as hardcoded hex here.
export function themeColor(name, fallback = "#888888") {
  if (typeof window === "undefined") return fallback;
  const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return value || fallback;
}

// js/heatmap.js
// Risk color scale and classification utilities
const Heatmap = (() => {
  // Enhanced gradient stops for richer visual mapping
  // Blue (deficit) → Teal (normal) → Amber → Red (bloom)
  const STOPS = [
    { z: -3.0, r: 30,  g: 58,  b: 138 },   // deep indigo-blue
    { z: -2.0, r: 14,  g: 116, b: 144 },   // dark cyan
    { z: -1.0, r: 20,  g: 184, b: 166 },   // teal
    { z:  0.0, r: 52,  g: 211, b: 153 },   // emerald-green (normal)
    { z:  1.0, r: 132, g: 204, b: 22  },   // lime
    { z:  1.5, r: 234, g: 179, b: 8   },   // amber
    { z:  2.0, r: 249, g: 115, b: 22  },   // orange
    { z:  2.5, r: 239, g: 68,  b: 68  },   // red
    { z:  3.0, r: 185, g: 28,  b: 28  },   // deep red (critical bloom)
  ];

  function lerp(a, b, t) { return a + (b - a) * t; }

  function zToColor(z) {
    const clamped = Math.max(-3, Math.min(3, z));
    for (let i = 0; i < STOPS.length - 1; i++) {
      const s0 = STOPS[i], s1 = STOPS[i + 1];
      if (clamped >= s0.z && clamped <= s1.z) {
        const t = (clamped - s0.z) / (s1.z - s0.z);
        const r = Math.round(lerp(s0.r, s1.r, t));
        const g = Math.round(lerp(s0.g, s1.g, t));
        const b = Math.round(lerp(s0.b, s1.b, t));
        return `rgb(${r},${g},${b})`;
      }
    }
    return 'rgb(185,28,28)';
  }

  function zToOpacity(z) {
    return Math.min(0.88, 0.25 + Math.abs(z) * 0.2);
  }

  function riskLabel(z) {
    if (z >= 2.5)  return { label: 'CRITICAL', cls: 'risk-critical', card: 'card-critical', badge: 'badge-critical' };
    if (z >= 1.5)  return { label: 'HIGH',     cls: 'risk-high',     card: 'card-high',     badge: 'badge-high' };
    if (z >= 0.8)  return { label: 'ELEVATED', cls: 'risk-elevated', card: 'card-elevated', badge: 'badge-elevated' };
    if (z <= -1.5) return { label: 'LOW',      cls: 'risk-normal',   card: 'card-normal',   badge: 'badge-normal' };
    return                { label: 'NORMAL',   cls: 'risk-normal',   card: 'card-normal',   badge: 'badge-normal' };
  }

  return { zToColor, zToOpacity, riskLabel };
})();
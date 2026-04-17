// js/heatmap.js
const Heatmap = (() => {
  // Maps z-score [-3, +3] to a colour gradient
  // Blue (deep deficit) → Teal (normal) → Yellow → Red (bloom)
  const STOPS = [
    { z: -3.0, r: 26,  g: 35,  b: 126 },   // deep blue
    { z: -1.5, r: 2,   g: 136, b: 209 },   // sky blue
    { z:  0.0, r: 38,  g: 166, b: 154 },   // teal (normal)
    { z:  1.5, r: 249, g: 168, b: 37  },   // amber
    { z:  3.0, r: 229, g: 57,  b: 53  },   // red (bloom)
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
    return 'rgb(229,57,53)';
  }

  function zToOpacity(z) {
    // More extreme anomaly = more opaque
    return Math.min(0.85, 0.2 + Math.abs(z) * 0.2);
  }

  function riskLabel(z) {
    if (z >= 2.5)  return { label: 'CRITICAL', cls: 'risk-high' };
    if (z >= 1.5)  return { label: 'HIGH',     cls: 'risk-high' };
    if (z >= 0.8)  return { label: 'MODERATE', cls: 'risk-med'  };
    if (z <= -1.5) return { label: 'LOW',      cls: '' };
    return { label: 'NORMAL', cls: '' };
  }

  return { zToColor, zToOpacity, riskLabel };
})();
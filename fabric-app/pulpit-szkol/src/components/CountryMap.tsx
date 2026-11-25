import { useMemo, useState } from 'react';

import { REGIONS } from '@/data/poland';
import { project } from '@/data/model';

export interface MapPoint {
  id: string;
  lat: number;
  lon: number;
  color: string;
  radius?: number;
  label: string;
}

export interface RegionStyle {
  fill: string;
  label?: string;
}

interface View {
  x: number;
  y: number;
  w: number;
}
const FULL: View = { x: 0, y: 0, w: 100 };

export function foldName(text: string): string {
  return text.replace(/ł/g, 'l').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
}

function clamp(v: View): View {
  const w = Math.min(100, Math.max(7, v.w));
  return { w, x: Math.min(100 - w, Math.max(0, v.x)), y: Math.min(100 - w, Math.max(0, v.y)) };
}

export interface CountryMapProps {
  /** Styl wypelnienia wojewodztwa wg kodu. */
  regionStyle: (code: string) => RegionStyle;
  /** Mapa nazwy (bez diakrytykow) na kod wojewodztwa. */
  codeByName: Map<string, string>;
  selected?: string;
  onSelect?: (code: string) => void;
  points?: MapPoint[];
  onPointClick?: (id: string) => void;
  /** Opis dla czytnikow ekranu. */
  ariaLabel: string;
}

export function CountryMap({ regionStyle, codeByName, selected, onSelect, points = [], onPointClick, ariaLabel }: CountryMapProps) {
  const [manual, setManual] = useState<View | null>(null);
  const [hover, setHover] = useState<string | null>(null);

  const selectedRegion = useMemo(
    () => (selected ? REGIONS.find((r) => codeByName.get(foldName(r.name)) === selected) : undefined),
    [selected, codeByName]
  );
  const auto: View = selectedRegion ? clamp({ w: 36, x: selectedRegion.cx - 18, y: selectedRegion.cy - 18 }) : FULL;
  const view = manual ?? auto;
  const k = view.w / 100;

  const zoom = (factor: number) => {
    const cx = view.x + view.w / 2;
    const cy = view.y + view.w / 2;
    const w = Math.min(100, Math.max(7, view.w / factor));
    setManual(clamp({ w, x: cx - w / 2, y: cy - w / 2 }));
  };

  return (
    <div className="relative">
      <svg
        viewBox={`${view.x} ${view.y} ${view.w} ${view.w}`}
        className="h-auto w-full rounded-md bg-white"
        role="group"
        aria-label={ariaLabel}
      >
        {REGIONS.map((r) => {
          const code = codeByName.get(foldName(r.name)) ?? '';
          const st = regionStyle(code);
          const isSel = code === selected;
          return (
            <g key={r.name}>
              <path
                d={r.path}
                fill={st.fill}
                stroke={isSel ? '#0b5247' : '#5b6966'}
                strokeWidth={(isSel ? 2.2 : hover === code ? 1.8 : 0.9) * k}
                strokeLinejoin="round"
                role="button"
                tabIndex={0}
                aria-label={`Województwo ${r.name}${st.label ? `, ${st.label}` : ''}`}
                aria-pressed={isSel}
                className="cursor-pointer"
                onMouseEnter={() => setHover(code)}
                onMouseLeave={() => setHover(null)}
                onClick={() => {
                  setManual(null);
                  onSelect?.(isSel ? '' : code);
                }}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    setManual(null);
                    onSelect?.(isSel ? '' : code);
                  }
                }}
              />
              {st.label && (
                <text x={r.cx} y={r.cy} textAnchor="middle" dominantBaseline="middle" fontSize={3.2 * Math.max(k, 0.4)} fontWeight="700" fill="#1a2422" pointerEvents="none">
                  {st.label}
                </text>
              )}
            </g>
          );
        })}
        {points.map((p) => {
          const { x, y } = project(p.lat, p.lon);
          return (
            <circle
              key={p.id}
              cx={x}
              cy={y}
              r={(p.radius ?? 1.1) * Math.max(k, 0.3)}
              fill={p.color}
              stroke="#ffffff"
              strokeWidth={0.25 * Math.max(k, 0.3)}
              className={onPointClick ? 'cursor-pointer' : undefined}
              onClick={() => onPointClick?.(p.id)}
              role={onPointClick ? 'button' : undefined}
              aria-label={p.label}
            >
              <title>{p.label}</title>
            </circle>
          );
        })}
      </svg>
      <div className="absolute right-2 top-2 flex flex-col gap-1">
        <button type="button" aria-label="Przybliż" onClick={() => zoom(1.6)} className="h-8 w-8 rounded bg-white text-lg font-semibold text-ink ring-1 ring-slate-400 hover:bg-bs-50">+</button>
        <button type="button" aria-label="Oddal" onClick={() => zoom(1 / 1.6)} className="h-8 w-8 rounded bg-white text-lg font-semibold text-ink ring-1 ring-slate-400 hover:bg-bs-50">−</button>
        <button type="button" aria-label="Cała Polska" onClick={() => { setManual(null); onSelect?.(''); }} className="h-8 w-8 rounded bg-white text-xs font-semibold text-ink ring-1 ring-slate-400 hover:bg-bs-50">PL</button>
      </div>
    </div>
  );
}

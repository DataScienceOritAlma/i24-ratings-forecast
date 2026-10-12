// 80% interval on a numeric scale. Numeric axes read left-to-right even in a
// Hebrew interface, so the bar is laid out LTR.

export function rangeScaleMax(...values: (number | null | undefined)[]) {
  const top = Math.max(0, ...values.map((v) => v ?? 0));
  return Math.max(5, Math.ceil(top * 1.15));
}

export default function RangeBar({
  low, high, point, avg = null, max, compact = false,
}: {
  low: number;
  high: number;
  point: number;
  avg?: number | null;
  // Pass a shared max when several bars should be comparable.
  max?: number;
  compact?: boolean;
}) {
  const scaleMax = max ?? rangeScaleMax(high, avg);
  const pct = (v: number) => Math.max(0, Math.min(100, (v / scaleMax) * 100));

  const bar = (
    <div
      dir="ltr"
      className={`relative ${compact ? "h-5" : "h-8"}`}
      role="img"
      aria-label={`תחזית ${point.toFixed(2)}, בטווח של ${low.toFixed(2)} עד ${high.toFixed(2)}${avg != null ? `, ממוצע היסטורי ${avg.toFixed(2)}` : ""}`}
    >
      <div className="absolute inset-x-0 top-1/2 -translate-y-1/2 h-2 rounded-full bg-slate-200" />
      <div
        className="absolute top-1/2 -translate-y-1/2 h-2 rounded-full bg-brand-primary/35"
        style={{ left: `${pct(low)}%`, width: `${Math.max(0, pct(high) - pct(low))}%` }}
      />
      {avg != null && (
        <div
          className="absolute top-1 bottom-1 w-0 border-l-2 border-dashed border-slate-500"
          style={{ left: `${pct(avg)}%` }}
        />
      )}
      <div
        className={`absolute top-1/2 -translate-x-1/2 -translate-y-1/2 rounded-full bg-brand-dark ring-2 ring-white ${compact ? "w-3 h-3" : "w-4 h-4"}`}
        style={{ left: `${pct(point)}%` }}
      />
    </div>
  );

  if (compact) return bar;

  return (
    <div className="mt-6">
      <div className="flex items-baseline justify-between text-xs mb-2">
        <span className="text-muted">טווח ביטחון של 80%</span>
        <span className="num font-bold text-ink" dir="ltr">
          {low.toFixed(2)} – {high.toFixed(2)}
        </span>
      </div>

      {bar}

      <div dir="ltr" className="flex justify-between text-[11px] text-muted num mt-1">
        <span>0</span>
        <span>{scaleMax / 2}</span>
        <span>{scaleMax}</span>
      </div>

      <ul className="flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-muted mt-2">
        <li className="inline-flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-brand-dark" aria-hidden="true" /> תחזית
        </li>
        <li className="inline-flex items-center gap-1.5">
          <span className="w-4 h-2 rounded-full bg-brand-primary/35" aria-hidden="true" /> טווח 80%
        </li>
        {avg != null && (
          <li className="inline-flex items-center gap-1.5">
            <span className="w-0 h-3 border-l-2 border-dashed border-slate-500" aria-hidden="true" /> ממוצע היסטורי
          </li>
        )}
      </ul>
    </div>
  );
}

// frontend/src/components/CompanyCard.jsx
// Displays one intelligence object — the main UI element judges will see.

import { RefreshCw } from "lucide-react";

const SIGNAL_STYLES = {
  BULLISH: { bg: "bg-emerald-900/40", text: "text-emerald-400", border: "border-emerald-700" },
  BEARISH: { bg: "bg-red-900/40",     text: "text-red-400",     border: "border-red-700"     },
  NEUTRAL: { bg: "bg-gray-800/60",    text: "text-gray-300",    border: "border-gray-600"    },
};

function SignalBadge({ signal }) {
  const s = SIGNAL_STYLES[signal] || SIGNAL_STYLES.NEUTRAL;
  return (
    <span className={`text-xs font-bold px-2.5 py-1 rounded-full border ${s.bg} ${s.text} ${s.border}`}>
      {signal}
    </span>
  );
}

function ConfidenceBar({ value }) {
  const color = value >= 70 ? "bg-emerald-500" : value >= 40 ? "bg-amber-500" : "bg-red-500";
  return (
    <div className="flex items-center gap-2 mt-1">
      <div className="flex-1 h-1.5 bg-gray-700 rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full transition-all`} style={{ width: `${value}%` }} />
      </div>
      <span className="text-xs text-gray-400 min-w-[28px] text-right">{value}%</span>
    </div>
  );
}

function SignalRow({ label, signal, detail }) {
  const s = SIGNAL_STYLES[signal] || SIGNAL_STYLES.NEUTRAL;
  return (
    <div className="flex items-start justify-between py-2 border-b border-gray-800 last:border-0">
      <div>
        <p className="text-xs text-gray-400">{label}</p>
        {detail && <p className="text-xs text-gray-500 mt-0.5">{detail}</p>}
      </div>
      <SignalBadge signal={signal} />
    </div>
  );
}

export default function CompanyCard({ ticker, company, data, loading, error, onRefresh }) {
  if (loading) {
    return (
      <div className="rounded-xl border border-gray-800 bg-gray-900 p-6 animate-pulse">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-lg bg-gray-800" />
          <div className="flex-1">
            <div className="h-4 bg-gray-800 rounded w-32 mb-2" />
            <div className="h-3 bg-gray-800 rounded w-20" />
          </div>
        </div>
        <div className="h-3 bg-gray-800 rounded w-full mb-2" />
        <div className="h-3 bg-gray-800 rounded w-4/5" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-xl border border-red-900 bg-red-950/30 p-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="font-bold text-white">{ticker}</p>
            <p className="text-sm text-red-400 mt-1">{error}</p>
          </div>
          <button onClick={onRefresh} className="text-gray-400 hover:text-white p-2 rounded-lg hover:bg-gray-800">
            <RefreshCw size={16} />
          </button>
        </div>
      </div>
    );
  }

  if (!data) return null;

  const { signals, confidence, composite_signal, key_risks, recommended_action, generated_at } = data;
  const age = generated_at
    ? Math.round((Date.now() - new Date(generated_at).getTime()) / 60000)
    : null;

  return (
    <div className={`rounded-xl border bg-gray-900 overflow-hidden ${SIGNAL_STYLES[composite_signal]?.border || "border-gray-700"}`}>
      {/* Card header */}
      <div className="p-5 flex items-start justify-between border-b border-gray-800">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-blue-900/50 border border-blue-800 flex items-center justify-center">
            <span className="text-xs font-bold text-blue-300">{ticker.slice(0, 2)}</span>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <p className="font-bold text-white">{ticker}</p>
              <SignalBadge signal={composite_signal} />
            </div>
            <p className="text-xs text-gray-400 mt-0.5">{company || data.company}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {age !== null && (
            <span className="text-xs text-gray-500">{age < 60 ? `${age}m ago` : `${Math.round(age/60)}h ago`}</span>
          )}
          <button
            onClick={onRefresh}
            className="text-gray-400 hover:text-white p-1.5 rounded-lg hover:bg-gray-800 transition-colors"
            title="Refresh intelligence"
          >
            <RefreshCw size={14} />
          </button>
        </div>
      </div>

      <div className="p-5 grid grid-cols-1 md:grid-cols-2 gap-5">
        {/* Left: confidence + signals */}
        <div>
          <p className="text-xs text-gray-400 mb-1 font-medium uppercase tracking-wide">Confidence</p>
          <ConfidenceBar value={confidence} />

          <div className="mt-4">
            <p className="text-xs text-gray-400 mb-2 font-medium uppercase tracking-wide">Signal breakdown</p>
            {signals && (
              <>
                <SignalRow
                  label="News sentiment"
                  signal={signals.news_sentiment?.label}
                  detail={`${signals.news_sentiment?.articles_analyzed || 0} articles`}
                />
                <SignalRow
                  label="Hiring trend"
                  signal={signals.hiring_trend?.signal}
                  detail={signals.hiring_trend?.jobs_30d != null ? `${signals.hiring_trend.jobs_30d} jobs (30d)` : ""}
                />
                <SignalRow
                  label="Filing language"
                  signal={signals.filing_language?.signal}
                  detail={signals.filing_language?.guidance_tone}
                />
                <SignalRow
                  label="Pricing intelligence"
                  signal={signals.pricing?.signal}
                />
              </>
            )}
          </div>
        </div>

        {/* Right: risks + action */}
        <div>
          {recommended_action && (
            <div className="mb-4">
              <p className="text-xs text-gray-400 mb-1.5 font-medium uppercase tracking-wide">Recommended action</p>
              <p className="text-sm text-white leading-relaxed">{recommended_action}</p>
            </div>
          )}
          {key_risks?.length > 0 && (
            <div>
              <p className="text-xs text-gray-400 mb-1.5 font-medium uppercase tracking-wide">Key risks</p>
              <ul className="space-y-1">
                {key_risks.slice(0, 4).map((risk, i) => (
                  <li key={i} className="text-xs text-gray-300 flex items-start gap-1.5">
                    <span className="text-red-500 mt-0.5 flex-shrink-0">•</span>
                    {risk}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

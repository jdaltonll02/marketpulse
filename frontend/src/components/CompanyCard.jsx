// frontend/src/components/CompanyCard.jsx
// Displays one intelligence object — the main UI element judges will see.

import { useState, useEffect } from "react";
import { RefreshCw, TrendingUp, TrendingDown, ArrowLeftRight, Activity, X, ChevronDown, ChevronUp } from "lucide-react";
import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis, ResponsiveContainer,
  LineChart, Line, XAxis, YAxis, Tooltip,
} from "recharts";
import { apiFetch } from "../api/client";

const SIG_VAL = { BULLISH: 85, NEUTRAL: 50, BEARISH: 15 };

function SignalRadar({ signals }) {
  if (!signals) return null;
  const data = [
    { subject: "News",    val: SIG_VAL[signals.news_sentiment?.label]    ?? 50 },
    { subject: "Hiring",  val: SIG_VAL[signals.hiring_trend?.signal]     ?? 50 },
    { subject: "Filing",  val: SIG_VAL[signals.filing_language?.signal]  ?? 50 },
    { subject: "Pricing", val: SIG_VAL[signals.pricing?.signal]          ?? 50 },
  ];
  return (
    <ResponsiveContainer width="100%" height={160}>
      <RadarChart data={data} margin={{ top: 8, right: 20, bottom: 8, left: 20 }}>
        <PolarGrid stroke="#374151" />
        <PolarAngleAxis dataKey="subject" tick={{ fill: "#9ca3af", fontSize: 10 }} />
        <Radar dataKey="val" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.25} />
      </RadarChart>
    </ResponsiveContainer>
  );
}

function SentimentBar({ score }) {
  if (score == null) return null;
  const pct   = ((score + 1) / 2) * 100;
  const color = score > 0.15 ? "#10b981" : score < -0.15 ? "#ef4444" : "#6b7280";
  return (
    <div className="mt-2 mb-3">
      <div className="flex justify-between text-xs text-gray-500 mb-1">
        <span>Bearish</span>
        <span style={{ color }} className="font-medium">{score.toFixed(2)}</span>
        <span>Bullish</span>
      </div>
      <div className="h-1.5 bg-gray-700 rounded-full relative">
        <div className="absolute top-0 bottom-0 w-px bg-gray-500" style={{ left: "50%" }} />
        <div
          className="h-full rounded-full absolute transition-all"
          style={{
            backgroundColor: color,
            left:  score < 0 ? `${pct}%` : "50%",
            width: `${Math.abs(score) * 50}%`,
          }}
        />
      </div>
    </div>
  );
}

function HistoryChart({ ticker }) {
  const [history, setHistory] = useState([]);
  useEffect(() => {
    apiFetch(`/api/intelligence/${ticker}/history`)
      .then(r => r.ok ? r.json() : [])
      .then(data => setHistory(data.map(d => ({
        t:    new Date(d.generated).toLocaleDateString("en-US", { month: "short", day: "numeric" }),
        conf: d.confidence,
        sig:  d.signal,
      }))))
      .catch(() => {});
  }, [ticker]);

  if (history.length < 2) return null;
  return (
    <div className="mt-4">
      <p className="text-xs text-gray-400 mb-2 font-medium uppercase tracking-wide">Confidence trend</p>
      <ResponsiveContainer width="100%" height={80}>
        <LineChart data={history} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
          <XAxis dataKey="t" tick={{ fill: "#6b7280", fontSize: 9 }} />
          <YAxis domain={[0, 100]} tick={{ fill: "#6b7280", fontSize: 9 }} />
          <Tooltip
            contentStyle={{ background: "#111827", border: "1px solid #374151", borderRadius: 6, fontSize: 11 }}
            labelStyle={{ color: "#9ca3af" }}
            formatter={v => [`${v}%`, "Confidence"]}
          />
          <Line type="monotone" dataKey="conf" stroke="#3b82f6" strokeWidth={2} dot={{ fill: "#3b82f6", r: 3 }} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

const DRIFT_CONFIG = {
  improved:         { icon: TrendingUp,       color: "text-emerald-400", bg: "bg-emerald-900/30 border-emerald-800", label: "Signal improved"    },
  deteriorated:     { icon: TrendingDown,     color: "text-red-400",     bg: "bg-red-900/30 border-red-800",         label: "Signal deteriorated" },
  reversed:         { icon: ArrowLeftRight,   color: "text-orange-400",  bg: "bg-orange-900/30 border-orange-800",   label: "Signal reversed"     },
  confidence_shift: { icon: Activity,         color: "text-blue-400",    bg: "bg-blue-900/30 border-blue-800",       label: "Confidence shifted"  },
};

function DriftBanner({ drift }) {
  if (!drift) return null;
  const cfg = DRIFT_CONFIG[drift.direction];
  if (!cfg) return null;
  const Icon = cfg.icon;
  return (
    <div className={`mx-5 mt-3 px-4 py-3 rounded-lg border ${cfg.bg} flex items-start gap-3`}>
      <Icon size={15} className={`${cfg.color} flex-shrink-0 mt-0.5`} />
      <div className="min-w-0">
        <div className="flex items-center gap-2 mb-0.5">
          <span className={`text-xs font-semibold ${cfg.color}`}>{cfg.label}</span>
          <span className="text-xs text-gray-500">
            was {drift.previous_signal} {drift.previous_confidence}%
          </span>
        </div>
        <p className="text-xs text-gray-300 leading-relaxed">{drift.explanation}</p>
      </div>
    </div>
  );
}

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

export default function CompanyCard({ ticker, company, data, loading, error, onRefresh, onRemove }) {
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

  const { signals, confidence, composite_signal, key_risks, recommended_action, generated_at, drift } = data;
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
          {onRemove && (
            <button
              onClick={onRemove}
              className="text-gray-600 hover:text-red-400 p-1.5 rounded-lg hover:bg-gray-800 transition-colors"
              title="Remove from watchlist"
            >
              <X size={14} />
            </button>
          )}
        </div>
      </div>

      <DriftBanner drift={drift} />

      <div className="p-5 grid grid-cols-1 md:grid-cols-3 gap-5">

        {/* Col 1: Signal radar */}
        <div>
          <p className="text-xs text-gray-400 mb-1 font-medium uppercase tracking-wide">Signal overview</p>
          <SignalRadar signals={signals} />
          <HistoryChart ticker={ticker} />
        </div>

        {/* Col 2: Confidence + signal rows */}
        <div>
          <p className="text-xs text-gray-400 mb-1 font-medium uppercase tracking-wide">Confidence</p>
          <ConfidenceBar value={confidence} />
          {signals && <SentimentBar score={signals.news_sentiment?.score} />}

          <div className="mt-3">
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
                  detail={`${signals.hiring_trend?.jobs_30d ?? 0} articles`}
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

          {/* Filing key phrases */}
          {signals?.filing_language?.key_phrases?.length > 0 && (
            <div className="mt-3">
              <p className="text-xs text-gray-400 mb-1.5 font-medium uppercase tracking-wide">Filing phrases</p>
              <ul className="space-y-1">
                {signals.filing_language.key_phrases.slice(0, 3).map((p, i) => (
                  <li key={i} className="text-xs text-gray-400 italic border-l-2 border-gray-700 pl-2">
                    "{p}"
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {/* Col 3: Action + risks */}
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
          {data?.data_sources_used?.length > 0 && (
            <div className="mt-4 pt-3 border-t border-gray-800">
              <p className="text-xs text-gray-500 mb-1 font-medium uppercase tracking-wide">Sources</p>
              <div className="flex flex-wrap gap-1">
                {data.data_sources_used.map((s, i) => (
                  <span key={i} className="text-xs px-1.5 py-0.5 bg-gray-800 text-gray-500 rounded">
                    {s}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// frontend/src/App.jsx
// MarketPulse AI — Main dashboard
// Shows intelligence objects for a watchlist of tickers.

import { useState, useEffect } from "react";
import CompanyCard   from "./components/CompanyCard";
import SearchBar     from "./components/SearchBar";
import LoadingSpinner from "./components/LoadingSpinner";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:5000";

// Default watchlist — shown on load
const DEFAULT_TICKERS = [
  { ticker: "AAPL",  company: "Apple Inc."            },
  { ticker: "MSFT",  company: "Microsoft Corporation" },
  { ticker: "NVDA",  company: "NVIDIA Corporation"    },
  { ticker: "META",  company: "Meta Platforms"        },
  { ticker: "GOOGL", company: "Alphabet Inc."         },
];

export default function App() {
  const [watchlist, setWatchlist]   = useState(DEFAULT_TICKERS);
  const [data,      setData]        = useState({});   // ticker → IntelligenceObject
  const [loading,   setLoading]     = useState({});   // ticker → bool
  const [error,     setError]       = useState({});   // ticker → string

  // Load all watchlist tickers on mount
  useEffect(() => {
    watchlist.forEach(({ ticker, company }) => fetchTicker(ticker, company));
  }, []);

  async function fetchTicker(ticker, company = "", refresh = false) {
    setLoading(prev => ({ ...prev, [ticker]: true }));
    setError(prev  => ({ ...prev, [ticker]: null }));

    const endpoint = refresh
      ? `${API_BASE}/api/intelligence/${ticker}/refresh`
      : `${API_BASE}/api/intelligence/${ticker}?company=${encodeURIComponent(company)}`;

    try {
      const resp = await fetch(endpoint);
      if (!resp.ok) throw new Error(`API error ${resp.status}`);
      const obj = await resp.json();
      setData(prev => ({ ...prev, [ticker]: obj }));
    } catch (e) {
      setError(prev => ({ ...prev, [ticker]: e.message }));
    } finally {
      setLoading(prev => ({ ...prev, [ticker]: false }));
    }
  }

  function addTicker(ticker, company) {
    const t = ticker.toUpperCase().trim();
    if (!t || watchlist.find(w => w.ticker === t)) return;
    setWatchlist(prev => [...prev, { ticker: t, company }]);
    fetchTicker(t, company);
  }

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      {/* Header */}
      <header className="border-b border-gray-800 px-6 py-4 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">MarketPulse AI</h1>
          <p className="text-xs text-gray-400 mt-0.5">Pre-earnings intelligence · powered by Bright Data + Claude</p>
        </div>
        <span className="text-xs bg-blue-900 text-blue-300 px-3 py-1 rounded-full font-medium">
          Track 2 · Finance & Market Intelligence
        </span>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-8">
        {/* Search */}
        <SearchBar onAdd={addTicker} />

        {/* Cards grid */}
        <div className="mt-8 grid grid-cols-1 gap-6">
          {watchlist.map(({ ticker, company }) => (
            <CompanyCard
              key={ticker}
              ticker={ticker}
              company={company}
              data={data[ticker]}
              loading={loading[ticker]}
              error={error[ticker]}
              onRefresh={() => fetchTicker(ticker, company, true)}
            />
          ))}
        </div>
      </main>
    </div>
  );
}

// frontend/src/components/SearchBar.jsx
import { useState } from "react";
import { Search } from "lucide-react";

export default function SearchBar({ onAdd }) {
  const [ticker,  setTicker]  = useState("");
  const [company, setCompany] = useState("");

  function handleSubmit(e) {
    e.preventDefault();
    if (!ticker.trim()) return;
    onAdd(ticker.toUpperCase().trim(), company.trim());
    setTicker("");
    setCompany("");
  }

  return (
    <form onSubmit={handleSubmit} className="flex gap-2">
      <div className="relative flex-1 max-w-xs">
        <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
        <input
          value={ticker}
          onChange={e => setTicker(e.target.value)}
          placeholder="Ticker (e.g. NVDA)"
          className="w-full pl-9 pr-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
        />
      </div>
      <input
        value={company}
        onChange={e => setCompany(e.target.value)}
        placeholder="Company name (optional)"
        className="flex-1 px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
      />
      <button
        type="submit"
        className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium rounded-lg transition-colors"
      >
        Add
      </button>
    </form>
  );
}

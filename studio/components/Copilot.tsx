"use client";

import { useState } from "react";
import { useStudioStore } from "@/lib/store";
import { Sparkles, X, Check, Zap } from "lucide-react";

export default function Copilot() {
  const { 
    suggestions, 
    isLoadingSuggestion, 
    acceptSuggestion, 
    dismissSuggestion,
    getSuggestion,
  } = useStudioStore();
  
  const [prompt, setPrompt] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (prompt.trim()) {
      getSuggestion(prompt);
      setPrompt("");
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-[#1a1a24] px-4 py-3">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-[#6366f1]" />
          <span className="font-medium">🤖 Copilot</span>
        </div>
        <span className="text-xs text-gray-500">⌘K</span>
      </div>
      
      {/* Input */}
      <form onSubmit={handleSubmit} className="p-3 border-b border-[#1a1a24]">
        <div className="relative">
          <input
            type="text"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="Ask Copilot... (e.g., 'add error handling')"
            className="w-full rounded-lg border border-[#1a1a24] bg-[#0f0f14] px-3 py-2 text-sm placeholder:text-gray-600 focus:border-[#6366f1] focus:outline-none"
          />
          <button
            type="submit"
            className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-500 hover:text-[#6366f1]"
          >
            <Zap className="w-4 h-4" />
          </button>
        </div>
      </form>
      
      {/* Suggestions */}
      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {isLoadingSuggestion ? (
          <div className="flex items-center gap-3 text-gray-400">
            <div className="animate-spin">
              <Sparkles className="w-4 h-4" />
            </div>
            <span className="text-sm">Thinking...</span>
          </div>
        ) : suggestions.length === 0 ? (
          <div className="text-center text-gray-500 py-8">
            <div className="text-3xl mb-2">💡</div>
            <div className="text-sm">No suggestions yet</div>
            <div className="text-xs mt-1">
              Press ⌘K or ask above
            </div>
          </div>
        ) : (
          suggestions.map((suggestion) => (
            <div
              key={suggestion.id}
              className="rounded-lg border border-[#1a1a24] bg-[#0f0f14] overflow-hidden copilot-suggestion"
            >
              {/* Header */}
              <div className="flex items-center justify-between px-3 py-2 bg-[#1a1a24]">
                <div className="flex items-center gap-2">
                  <span className="text-xs bg-[#6366f1]/20 text-[#6366f1] px-2 py-0.5 rounded">
                    {suggestion.type}
                  </span>
                  <span className="text-xs text-gray-500">
                    {Math.round(suggestion.confidence * 100)}% confidence
                  </span>
                </div>
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => acceptSuggestion(suggestion.id)}
                    className="p-1 text-green-400 hover:bg-green-400/10 rounded"
                    title="Accept"
                  >
                    <Check className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => dismissSuggestion(suggestion.id)}
                    className="p-1 text-gray-400 hover:bg-gray-400/10 rounded"
                    title="Dismiss"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              </div>
              
              {/* Content */}
              <div className="p-3">
                <pre className="text-sm text-gray-300 whitespace-pre-wrap font-mono">
                  {suggestion.text}
                </pre>
              </div>
            </div>
          ))
        )}
      </div>
      
      {/* Footer */}
      <div className="border-t border-[#1a1a24] px-3 py-2">
        <div className="flex items-center justify-between text-xs text-gray-500">
          <span>Powered by Claude</span>
          <span>Latency: ~180ms</span>
        </div>
      </div>
    </div>
  );
}

import React, { useEffect, useState } from 'react';
import { AlertTriangle, CheckCircle2, RefreshCw, Layers, ThumbsUp, ArrowRight } from 'lucide-react';
import { useAppStore } from '../store/useAppStore';
import { api } from '../services/api';
import { ReviewItem } from '../types';

export const ReviewQueue: React.FC = () => {
  const { activeProject, setCurrentView } = useAppStore();
  const [items, setItems] = useState<ReviewItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const loadQueue = async () => {
    if (!activeProject) return;
    setIsLoading(true);
    try {
      const q = await api.getReviewQueue(activeProject.id);
      setItems(q);
    } catch (e) {
      console.error(e);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadQueue();
  }, [activeProject]);

  const handleCorrect = async (item: ReviewItem, newType: string) => {
    if (!activeProject) return;
    try {
      await api.submitCorrection(
        activeProject.id,
        item.block_id,
        newType,
        item.block_type,
        item.full_text
      );
      // Remove corrected item from UI list
      setItems((prev) => prev.filter((i) => i.block_id !== item.block_id));
    } catch (err) {
      alert('Failed to save correction.');
    }
  };

  if (!activeProject) {
    return (
      <div className="flex-1 flex items-center justify-center p-8 text-slate-400">
        <p>No active project selected.</p>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-6 md:p-8 space-y-6 max-w-6xl mx-auto w-full">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800/80 pb-6">
        <div>
          <span className="text-xs px-2 py-0.5 rounded bg-amber-500/10 border border-amber-500/20 text-amber-400 font-medium">
            Human-in-the-Loop Triage
          </span>
          <h1 className="text-2xl font-bold text-white mt-1">Classification Review Queue</h1>
          <p className="text-xs text-slate-400 mt-1">
            Review elements flagged with lower confidence or ambiguous structural boundaries. Corrections update local learning models.
          </p>
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={loadQueue}
            disabled={isLoading}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium border border-slate-700 transition"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin text-sky-400' : ''}`} />
            <span>Refresh</span>
          </button>

          <button
            onClick={() => setCurrentView('preview')}
            className="flex items-center space-x-1.5 px-3.5 py-1.5 rounded-xl bg-sky-500/15 border border-sky-500/30 text-sky-400 hover:bg-sky-500/25 text-xs font-medium transition"
          >
            <span>Preview Book</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Queue Status */}
      {items.length === 0 ? (
        <div className="glass-card rounded-2xl p-12 text-center border border-slate-800">
          <CheckCircle2 className="w-12 h-12 text-emerald-400 mx-auto mb-3" />
          <h3 className="text-base font-semibold text-slate-200">Review Queue Clear</h3>
          <p className="text-xs text-slate-400 max-w-sm mx-auto mt-1 mb-4">
            All document blocks in this manuscript have been resolved with high confidence by the Hybrid ML and Rule cascade.
          </p>
          <button
            onClick={() => setCurrentView('preview')}
            className="px-4 py-2 rounded-xl bg-sky-500 hover:bg-sky-400 text-white text-xs font-medium transition"
          >
            Proceed to Book Preview
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>{items.length} Uncertain Elements Requiring Verification</span>
            <span>Click any role button to reclassify</span>
          </div>

          <div className="space-y-3">
            {items.map((item, idx) => (
              <div
                key={item.block_id}
                className="glass-card rounded-xl p-5 border border-slate-800 hover:border-slate-700 transition space-y-3"
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-center space-x-2.5">
                    <span className="w-6 h-6 rounded-lg bg-slate-800 text-slate-300 flex items-center justify-center text-xs font-mono">
                      #{idx + 1}
                    </span>
                    <div>
                      <div className="flex items-center space-x-2">
                        <span className="text-xs font-semibold text-slate-200">
                          Predicted: <span className="text-sky-400 font-mono">{item.block_type}</span>
                        </span>
                        <span className="text-[11px] px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20 font-mono">
                          Confidence: {Math.round(item.confidence * 100)}%
                        </span>
                      </div>
                      <span className="text-[10px] text-slate-500">
                        Page ~{item.estimated_page} • Block #{item.original_index}
                      </span>
                    </div>
                  </div>

                  <button
                    onClick={() => handleCorrect(item, item.block_type)}
                    className="flex items-center space-x-1 px-2.5 py-1 rounded-lg bg-slate-800/80 hover:bg-emerald-500/20 hover:text-emerald-400 text-slate-400 text-xs transition"
                  >
                    <ThumbsUp className="w-3.5 h-3.5" />
                    <span>Accept As-Is</span>
                  </button>
                </div>

                {/* Snippet preview */}
                <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-900 font-serif text-slate-200 text-sm italic leading-relaxed">
                  "{item.full_text || item.text_preview}"
                </div>

                {/* Action Buttons */}
                <div className="flex flex-wrap items-center gap-1.5 pt-1">
                  <span className="text-[11px] text-slate-500 mr-1">Reclassify as:</span>
                  {[
                    { id: 'CHAPTER_TITLE', label: 'Chapter Title' },
                    { id: 'HEADING_1', label: 'Heading 1' },
                    { id: 'HEADING_2', label: 'Heading 2' },
                    { id: 'BODY', label: 'Body Text' },
                    { id: 'QUOTE', label: 'Quote' },
                    { id: 'CAPTION', label: 'Caption' },
                  ].map((btn) => (
                    <button
                      key={btn.id}
                      onClick={() => handleCorrect(item, btn.id)}
                      className={`px-2.5 py-1 rounded-lg text-xs font-medium transition border ${
                        item.block_type === btn.id
                          ? 'bg-sky-500/10 text-sky-400 border-sky-500/30'
                          : 'bg-slate-900 text-slate-300 border-slate-800 hover:bg-slate-800 hover:border-slate-700'
                      }`}
                    >
                      {btn.label}
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

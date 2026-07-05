import { useEffect, useState } from 'react';
import { CheckCircle2, Zap } from 'lucide-react';

const STEP_INTERVAL_MS = 2400;

// Efficiency-themed animated loading page: concentric spinning rings, a live
// step checklist, and a shimmering progress bar that never quite claims 100%.
export default function LoadingScreen({ title, steps }) {
  const [stepIndex, setStepIndex] = useState(0);

  useEffect(() => {
    setStepIndex(0);
    const id = setInterval(
      () => setStepIndex((i) => Math.min(i + 1, steps.length - 1)),
      STEP_INTERVAL_MS
    );
    return () => clearInterval(id);
  }, [steps]);

  const progress = Math.min(12 + ((stepIndex + 1) / steps.length) * 80, 92);

  return (
    <div className="bg-white border border-[#E5E5EA] rounded-2xl p-12 flex flex-col items-center justify-center min-h-[450px] shadow-[0_4px_24px_rgba(0,0,0,0.01)] animate-fadeIn">

      {/* Concentric ring spinner with a pulsing energy core */}
      <div className="relative w-20 h-20 mb-6">
        <div className="absolute inset-0 rounded-full border-2 border-[#E5E5EA] border-t-neutral-900 animate-spin"></div>
        <div className="absolute inset-2.5 rounded-full border-2 border-[#E5E5EA] border-b-blue-600 cf-spin-reverse"></div>
        <div className="absolute inset-0 flex items-center justify-center text-blue-600 cf-pulse-core">
          <Zap size={20} fill="currentColor" />
        </div>
      </div>

      <h3 className="text-sm font-semibold text-[#1D1D1F] mb-1">{title}</h3>
      <p className="text-xs text-[#86868B] font-medium mb-7">Optimized pipeline engaged — hang tight.</p>

      {/* Live step checklist */}
      <div className="w-full max-w-xs space-y-2.5 mb-7">
        {steps.map((step, i) => (
          <div
            key={step}
            className={`flex items-center gap-2.5 text-xs font-medium transition-all duration-500 ${
              i < stepIndex ? 'text-emerald-600' : i === stepIndex ? 'text-[#1D1D1F]' : 'text-[#C7C7CC]'
            }`}
          >
            {i < stepIndex ? (
              <CheckCircle2 size={14} className="shrink-0" />
            ) : (
              <span
                className={`w-3.5 h-3.5 rounded-full border-2 shrink-0 ${
                  i === stepIndex ? 'border-blue-600 cf-pulse-core' : 'border-[#E5E5EA]'
                }`}
              ></span>
            )}
            {step}
            {i === stepIndex && <span className="cf-ellipsis"></span>}
          </div>
        ))}
      </div>

      {/* Shimmering progress bar */}
      <div className="w-full max-w-xs h-1.5 bg-[#F5F5F7] rounded-full overflow-hidden">
        <div
          className="h-full rounded-full bg-neutral-900 cf-shimmer transition-all duration-1000 ease-out"
          style={{ width: `${progress}%` }}
        ></div>
      </div>
    </div>
  );
}

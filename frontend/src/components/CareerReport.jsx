import { AlertTriangle, ArrowLeft, Briefcase, ExternalLink, TrendingUp } from 'lucide-react';

const SEVERITY_STYLES = {
  high: 'bg-rose-50/60 border-rose-500/15 text-rose-700',
  medium: 'bg-amber-50/60 border-amber-500/15 text-amber-700',
  low: 'bg-blue-50/50 border-blue-500/10 text-blue-700',
};

const scoreColor = (score) =>
  score >= 80 ? 'text-emerald-600' : score >= 60 ? 'text-amber-600' : 'text-rose-600';

// ATS scan results: score, issues, enhancement suggestions, and recommended
// roles deep-linked into LinkedIn/Indeed search.
export default function CareerReport({ report, onBack }) {
  return (
    <div className="space-y-6 animate-fadeIn max-w-3xl mx-auto">

      {/* Score header */}
      <div className="bg-neutral-900 p-6 rounded-2xl text-white relative overflow-hidden">
        <button
          onClick={onBack}
          className="absolute top-5 right-5 text-[#86868B] hover:text-white text-xs font-medium inline-flex items-center gap-1 cursor-pointer transition-colors"
        >
          <ArrowLeft size={13} /> Back to planner
        </button>
        <span className="text-[10px] font-bold tracking-widest text-blue-400 uppercase">ATS Resume Audit</span>
        <div className="flex items-end gap-3 mt-2">
          <span className={`text-5xl font-bold tracking-tight ${scoreColor(report.ats_score)}`}>
            {report.ats_score}
          </span>
          <span className="text-sm text-[#86868B] font-medium pb-1.5">/ 100 ATS score</span>
        </div>
        {report.summary && (
          <p className="text-xs text-[#A1A1A6] font-medium leading-relaxed mt-3 border-t border-neutral-800 pt-3 max-w-xl">
            {report.summary}
          </p>
        )}
      </div>

      {/* Issues found by the scan */}
      {report.issues?.length > 0 && (
        <div className="bg-white border border-[#E5E5EA] rounded-2xl p-5 space-y-3">
          <h3 className="text-xs font-bold text-[#86868B] tracking-wider uppercase flex items-center gap-1.5">
            <AlertTriangle size={13} /> Scan Findings
          </h3>
          {report.issues.map((item, i) => (
            <div key={i} className={`border rounded-xl p-3.5 text-xs font-medium ${SEVERITY_STYLES[item.severity] || SEVERITY_STYLES.low}`}>
              <div className="flex items-center gap-2 mb-1">
                <span className="text-[9px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded bg-white/60 border border-current/10">
                  {item.severity}
                </span>
                <span className="font-semibold">{item.issue}</span>
              </div>
              <p className="text-[#515154] leading-relaxed">{item.fix}</p>
            </div>
          ))}
        </div>
      )}

      {/* Enhancement suggestions */}
      {report.enhancements?.length > 0 && (
        <div className="bg-white border border-[#E5E5EA] rounded-2xl p-5 space-y-2.5">
          <h3 className="text-xs font-bold text-[#86868B] tracking-wider uppercase flex items-center gap-1.5">
            <TrendingUp size={13} /> Resume Enhancements
          </h3>
          <ul className="space-y-2">
            {report.enhancements.map((tip, i) => (
              <li key={i} className="text-xs font-medium text-[#515154] leading-relaxed bg-[#F5F5F7]/60 border border-[#E5E5EA]/50 rounded-xl p-3">
                {tip}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Role matches with live search deep-links */}
      {report.recommended_roles?.length > 0 && (
        <div className="bg-white border border-[#E5E5EA] rounded-2xl p-5 space-y-3">
          <h3 className="text-xs font-bold text-[#86868B] tracking-wider uppercase flex items-center gap-1.5">
            <Briefcase size={13} /> Recommended Roles
          </h3>
          {report.recommended_roles.map((role, i) => (
            <div key={i} className="border border-[#E5E5EA] rounded-xl p-4 hover:border-[#D2D2D7] transition-all">
              <h4 className="text-sm font-semibold text-[#1D1D1F]">{role.title}</h4>
              <p className="text-xs text-[#515154] font-medium leading-relaxed mt-1">{role.reason}</p>
              {role.keywords && (
                <p className="text-[11px] text-[#86868B] font-medium mt-1.5">
                  <strong className="text-neutral-700">ATS keywords:</strong> {role.keywords}
                </p>
              )}
              <div className="flex gap-2 mt-3">
                <a
                  href={role.linkedin_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 text-[11px] font-semibold text-white bg-[#0A66C2] hover:bg-[#004182] px-3 py-1.5 rounded-lg transition-all"
                >
                  LinkedIn Jobs <ExternalLink size={11} />
                </a>
                <a
                  href={role.indeed_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 text-[11px] font-semibold text-white bg-[#003A9B] hover:bg-[#062e6f] px-3 py-1.5 rounded-lg transition-all"
                >
                  Indeed <ExternalLink size={11} />
                </a>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

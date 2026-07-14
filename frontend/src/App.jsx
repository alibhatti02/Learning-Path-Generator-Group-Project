import React, { useState, useEffect } from 'react';
import {
  Sparkles,
  Layers,
  Clock,
  Calendar,
  BookOpen,
  Flag,
  CheckCircle2,
  XCircle,
  X,
  ArrowRight,
  RotateCcw,
  Video, // NEW: Imported Video icon to distinguish live YouTube streaming items
  LogOut,
  Lock,
  Download,
  FileText,
  Upload,
  ScanSearch,
  History,
  Plus,
  Trash2,
  Users
} from 'lucide-react';
import LoadingScreen from './components/LoadingScreen';
import CareerReport from './components/CareerReport';
import GroupSkills from './components/GroupSkills';
import { downloadRoadmapMarkdown, printRoadmapPdf } from './utils/roadmapExport';

const BACKEND_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

// Step scripts for the animated loading page — one per long-running action
const ROADMAP_STEPS = [
  'Gauging topic complexity',
  'Calculating your optimal timeline',
  'Structuring weekly milestones',
  'Sourcing live video resources',
  'Polishing the blueprint',
];
const QUIZ_STEPS = ['Reviewing the milestone', 'Writing challenge questions', 'Calibrating difficulty'];
const GRADE_STEPS = ['Checking your answers', 'Writing per-question feedback', 'Scoring the assessment'];
const RESUME_STEPS = ['Parsing your resume', 'Running the ATS scan', 'Drafting enhancements', 'Matching job roles'];

export default function App() {
  // =========================================================================
  // NEW: Account session states — JWT persisted in localStorage
  // =========================================================================
  const [authToken, setAuthToken] = useState(() => localStorage.getItem('cf_token'));
  const [userEmail, setUserEmail] = useState(() => localStorage.getItem('cf_email'));
  const [authMode, setAuthMode] = useState('login'); // login | register
  const [authEmail, setAuthEmail] = useState('');
  const [authPassword, setAuthPassword] = useState('');
  const [authError, setAuthError] = useState('');
  const [authLoading, setAuthLoading] = useState(false);

  // Input Form States
  const [goal, setGoal] = useState('');
  const [experienceLevel, setExperienceLevel] = useState('beginner');

  // =========================================================================
  // CHANGED: Tracking "Hours Per Day" intervals to align with backend service contracts
  // =========================================================================
  const [hoursPerDay, setHoursPerDay] = useState(2);

  // UI Flow Control States
  const [viewState, setViewState] = useState('prompt'); // prompt | loading | roadmap | quiz | career
  const [loadingMessage, setLoadingMessage] = useState('');
  const [loadingSteps, setLoadingSteps] = useState(ROADMAP_STEPS);

  // Data Payload Storage States
  const [roadmapData, setRoadmapData] = useState(null);
  const [activeQuiz, setActiveQuiz] = useState(null);
  const [quizAnswers, setQuizAnswers] = useState({}); // { question_number: string }
  const [quizResult, setQuizResult] = useState(null);

  // NEW: Career Boost states — resume file + ATS scan report
  const [resumeFile, setResumeFile] = useState(null);
  const [careerReport, setCareerReport] = useState(null);

  // NEW: Saved session states — every generated roadmap persists server-side
  const [savedPaths, setSavedPaths] = useState([]);
  const [activePathId, setActivePathId] = useState(null);

  // Everything interactive locks while a generation request is in flight
  const isBusy = viewState === 'loading';

  // =========================================================================
  // NEW: Session history — fetch the user's saved roadmaps on login
  // =========================================================================
  const refreshSavedPaths = async (token = authToken) => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/paths`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (response.ok) setSavedPaths(await response.json());
    } catch {
      // History is a convenience — never block the app if it can't load
    }
  };

  useEffect(() => {
    if (authToken) refreshSavedPaths();
  }, [authToken]); // eslint-disable-line react-hooks/exhaustive-deps

  // Action: Load a past session — restores the roadmap and its original parameters
  const handleLoadPath = async (pathId) => {
    if (isBusy) return;
    try {
      const response = await authFetch(`${BACKEND_URL}/api/paths/${pathId}`);
      if (!response.ok) throw new Error('Could not load that session.');
      const record = await response.json();
      setRoadmapData(record.roadmap);
      setGoal(record.topic);
      setExperienceLevel(record.experience_level);
      setHoursPerDay(record.hours_per_day);
      setActivePathId(record.id);
      setActiveQuiz(null);
      setQuizResult(null);
      setViewState('roadmap');
    } catch (err) {
      alert(err.message);
    }
  };

  // Action: Delete a saved session
  const handleDeletePath = async (e, pathId) => {
    e.stopPropagation(); // don't also trigger the row's load handler
    if (!confirm('Delete this learning path? This cannot be undone.')) return;
    try {
      await authFetch(`${BACKEND_URL}/api/paths/${pathId}`, { method: 'DELETE' });
      setSavedPaths(savedPaths.filter((p) => p.id !== pathId));
      if (pathId === activePathId) {
        setActivePathId(null);
        setRoadmapData(null);
        setViewState('prompt');
      }
    } catch {
      alert('Failed to delete the session.');
    }
  };

  // Action: Register or log in, then persist the session token
  const handleAuthSubmit = async (e) => {
    e.preventDefault();
    setAuthError('');
    setAuthLoading(true);
    try {
      const response = await fetch(`${BACKEND_URL}/api/auth/${authMode}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: authEmail, password: authPassword })
      });
      const data = await response.json();
      if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Authentication failed. Check your details.');
      localStorage.setItem('cf_token', data.access_token);
      localStorage.setItem('cf_email', data.email);
      setAuthToken(data.access_token);
      setUserEmail(data.email);
      setAuthPassword('');
    } catch (err) {
      setAuthError(err.message);
    } finally {
      setAuthLoading(false);
    }
  };

  // Action: Clear the session and return to the login gate
  const handleLogout = () => {
    localStorage.removeItem('cf_token');
    localStorage.removeItem('cf_email');
    setAuthToken(null);
    setUserEmail(null);
    setRoadmapData(null);
    setActiveQuiz(null);
    setCareerReport(null);
    setResumeFile(null);
    setSavedPaths([]);
    setActivePathId(null);
    setViewState('prompt');
  };

  // Wrapper around fetch that attaches the JWT and logs out on expired/invalid sessions
  const authFetch = async (url, options = {}) => {
    const response = await fetch(url, {
      ...options,
      headers: { ...(options.headers || {}), Authorization: `Bearer ${authToken}` }
    });
    if (response.status === 401) {
      handleLogout();
      throw new Error('Your session expired — please log in again.');
    }
    return response;
  };

  // Action: Trigger Dynamic AI Roadmap Generation
  const handleGeneratePath = async (e) => {
    e.preventDefault();
    if (isBusy) return; // guard against double-submits interrupting an active run
    setLoadingMessage('Architecting your journey with Azure OpenAI');
    setLoadingSteps(ROADMAP_STEPS);
    setViewState('loading');

    try {
      // =========================================================================
      // CHANGED: Endpoint matched to production API path `/api/generate`
      // CHANGED: Parameters updated to pass `hours_per_day` instead of `weekly_hours`
      // =========================================================================
      const response = await authFetch(`${BACKEND_URL}/api/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          topic: goal,
          experience_level: experienceLevel,
          hours_per_day: hoursPerDay
        })
      });

      if (!response.ok) throw new Error('Network validation fail');
      const data = await response.json();
      setRoadmapData(data);
      setActivePathId(data.path_id || null);
      refreshSavedPaths(); // the backend auto-saved this run as a new session
      setViewState('roadmap');

    } catch (err) {
      alert(`Frontend Error: ${err.message}`);
      setViewState('prompt');
    }
  };

  // Action: Fetch Dynamic Quiz Schema
  const handleFetchQuiz = async (milestone, weekNum) => {
    if (isBusy) return;
    setLoadingMessage('Assembling milestone assessment');
    setLoadingSteps(QUIZ_STEPS);
    setViewState('loading');

    try {
      const response = await authFetch(`${BACKEND_URL}/api/quiz/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ milestone, week_number: weekNum })
      });
      const data = await response.json();
      setActiveQuiz(data);
      setQuizAnswers({});
      setQuizResult(null);
      setViewState('quiz');
    } catch (err) {
      alert('Failed to load quiz details.');
      setViewState('roadmap');
    }
  };

  // Action: Post Quiz Answers for AI Grading
  const handleQuizSubmit = async (e) => {
    e.preventDefault();
    if (isBusy) return;
    setLoadingMessage('Analyzing answers and writing deep feedback');
    setLoadingSteps(GRADE_STEPS);
    setViewState('loading');

    const formattedAnswers = activeQuiz.questions.map(q => ({
      question_number: q.question_number,
      answer: quizAnswers[q.question_number] || ''
    }));

    try {
      const response = await authFetch(`${BACKEND_URL}/api/quiz/submit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        // Server grades against the questions it stored at generation time —
        // we only send back which quiz and the user's answers.
        body: JSON.stringify({
          quiz_id: activeQuiz.quiz_id,
          answers: formattedAnswers
        })
      });
      const data = await response.json();
      setQuizResult(data);
      setViewState('quiz');
    } catch (err) {
      alert('Submission error encountered.');
      setViewState('roadmap');
    }
  };

  // =========================================================================
  // NEW: Career Boost — upload resume, run the GPT-5 ATS scan, show the report
  // =========================================================================
  const handleAnalyzeResume = async () => {
    if (!resumeFile || isBusy) return;
    setLoadingMessage('Auditing your resume with GPT-5');
    setLoadingSteps(RESUME_STEPS);
    setViewState('loading');

    try {
      const formData = new FormData();
      formData.append('file', resumeFile);
      // No Content-Type header — the browser sets the multipart boundary itself
      const response = await authFetch(`${BACKEND_URL}/api/resume/analyze`, {
        method: 'POST',
        body: formData
      });
      const data = await response.json();
      if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Resume analysis failed.');
      setCareerReport(data);
      setViewState('career');
    } catch (err) {
      alert(`Resume scan failed: ${err.message}`);
      setViewState('prompt');
    }
  };

  // =========================================================================
  // NEW: Roadmap export actions — Markdown file + print-to-PDF
  // =========================================================================
  const exportMeta = { level: experienceLevel, hoursPerDay };

  // =========================================================================
  // NEW: Account gate — unauthenticated visitors see the login/register card
  // =========================================================================
  if (!authToken) {
    return (
      <div className="bg-[#F5F5F7] text-[#1D1D1F] min-h-screen flex items-center justify-center font-sans p-4">
        <div className="bg-white border border-[#E5E5EA] rounded-2xl p-8 w-full max-w-sm shadow-[0_4px_24px_rgba(0,0,0,0.04)] space-y-6">
          <div className="text-center space-y-2">
            <div className="bg-neutral-900 text-white p-2.5 rounded-xl inline-flex">
              <Layers size={22} className="stroke-[2.2]" />
            </div>
            <h1 className="text-lg font-semibold tracking-tight">Course Forge</h1>
            <p className="text-xs text-[#86868B] font-medium">
              {authMode === 'login' ? 'Sign in to access your learning paths' : 'Create an account to get started'}
            </p>
          </div>

          <form onSubmit={handleAuthSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-[#86868B] mb-2">EMAIL</label>
              <input
                type="email"
                value={authEmail}
                onChange={(e) => setAuthEmail(e.target.value)}
                required
                placeholder="you@example.com"
                className="w-full p-3 bg-[#F5F5F7] border border-transparent rounded-xl focus:outline-hidden focus:border-blue-500 focus:bg-white text-sm transition-all font-medium placeholder-[#86868B]/70"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-[#86868B] mb-2">PASSWORD</label>
              <input
                type="password"
                value={authPassword}
                onChange={(e) => setAuthPassword(e.target.value)}
                required
                minLength={8}
                placeholder="Minimum 8 characters"
                className="w-full p-3 bg-[#F5F5F7] border border-transparent rounded-xl focus:outline-hidden focus:border-blue-500 focus:bg-white text-sm transition-all font-medium placeholder-[#86868B]/70"
              />
            </div>

            {authError && (
              <p className="text-xs text-rose-600 font-medium bg-rose-50/60 border border-rose-500/10 p-2.5 rounded-xl">{authError}</p>
            )}

            <button
              type="submit"
              disabled={authLoading}
              className="w-full bg-neutral-900 hover:bg-neutral-800 disabled:opacity-50 text-white font-medium py-3 rounded-xl transition-all cursor-pointer flex items-center justify-center gap-2 text-sm"
            >
              <Lock size={14} /> {authLoading ? 'Please wait...' : authMode === 'login' ? 'Sign In' : 'Create Account'}
            </button>
          </form>

          <p className="text-xs text-center text-[#86868B] font-medium">
            {authMode === 'login' ? "Don't have an account?" : 'Already have an account?'}{' '}
            <button
              type="button"
              onClick={() => { setAuthMode(authMode === 'login' ? 'register' : 'login'); setAuthError(''); }}
              className="text-blue-600 font-semibold hover:underline cursor-pointer"
            >
              {authMode === 'login' ? 'Sign up' : 'Sign in'}
            </button>
          </p>
        </div>
      </div>
    );
  }

  // =========================================================================
  // Shared parameters form card — full-width on the prompt page, sidebar in
  // the workspace. Every control locks while a request is in flight.
  // =========================================================================
  const parametersCard = (
    <section className="bg-white p-6 rounded-2xl border border-[#E5E5EA] shadow-[0_4px_24px_rgba(0,0,0,0.02)]">
      <h2 className="text-sm font-semibold tracking-wide text-[#1D1D1F] uppercase mb-4 flex items-center gap-1.5">
        Parameters
      </h2>
      <form onSubmit={handleGeneratePath} className="space-y-5">
        <div>
          <label className="block text-xs font-semibold text-[#86868B] mb-2">TARGET EXPERTISE</label>
          <textarea
            value={goal}
            onChange={(e) => setGoal(e.target.value)}
            rows={3}
            required
            disabled={isBusy}
            placeholder="e.g., Python backend development with FastAPI, building relational SQL databases, and setting up Docker container systems..."
            className="w-full p-3 bg-[#F5F5F7] border border-transparent rounded-xl focus:outline-hidden focus:border-blue-500 focus:bg-white text-sm transition-all resize-none placeholder-[#86868B]/70 font-medium disabled:opacity-50"
          />
        </div>

        <div>
          <label className="block text-xs font-semibold text-[#86868B] mb-2">EXPERIENCE PROFILE</label>
          <div className="grid grid-cols-3 gap-1.5 p-1 bg-[#F5F5F7] rounded-xl border border-[#E5E5EA]/40">
            {['beginner', 'intermediate', 'advanced'].map((lvl) => (
              <button
                key={lvl}
                type="button"
                onClick={() => setExperienceLevel(lvl)}
                disabled={isBusy}
                className={`text-xs py-2 rounded-lg font-medium capitalize transition-all cursor-pointer disabled:opacity-50 ${
                  experienceLevel === lvl
                    ? 'bg-white text-neutral-900 shadow-xs border border-[#E5E5EA]'
                    : 'text-[#86868B] hover:text-[#1D1D1F]'
                }`}
              >
                {lvl}
              </button>
            ))}
          </div>
        </div>

        <div>
          <div className="flex justify-between items-center mb-1">
            {/* =========================================================================
                CHANGED: UI label and slider constraints updated to manage Daily Commitment
                ========================================================================= */}
            <label className="block text-xs font-semibold text-[#86868B]">DAILY TIME COMMITMENT</label>
            <span className="text-xs font-bold text-blue-600">{hoursPerDay} hrs/day</span>
          </div>
          <input
            type="range"
            min={1}
            max={8}
            value={hoursPerDay}
            disabled={isBusy}
            onChange={(e) => setHoursPerDay(parseInt(e.target.value))}
            className="w-full h-1 bg-[#E5E5EA] rounded-lg appearance-none cursor-pointer accent-blue-600 disabled:opacity-50"
          />
        </div>

        <button
          type="submit"
          disabled={isBusy}
          className="w-full bg-neutral-900 hover:bg-neutral-800 disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium py-3 rounded-xl transition-all shadow-md shadow-neutral-900/10 cursor-pointer flex items-center justify-center gap-2 text-sm"
        >
          <Sparkles size={16} /> {isBusy ? 'Generating...' : 'Generate Roadmap'}
        </button>
      </form>
    </section>
  );

  // NEW: Career Boost upload card — lives on the prompt page under Parameters
  const careerBoostCard = (
    <section className="bg-white p-6 rounded-2xl border border-[#E5E5EA] shadow-[0_4px_24px_rgba(0,0,0,0.02)]">
      <h2 className="text-sm font-semibold tracking-wide text-[#1D1D1F] uppercase mb-1 flex items-center gap-1.5">
        Career Boost
      </h2>
      <p className="text-xs text-[#86868B] font-medium mb-4 leading-relaxed">
        Upload your resume — GPT-5 runs an ATS error scan, suggests enhancements, and matches you to live LinkedIn & Indeed job searches.
      </p>
      <div className="flex flex-col sm:flex-row gap-2.5">
        <label className={`flex-1 flex items-center justify-center gap-2 p-3 bg-[#F5F5F7] hover:bg-[#E5E5EA]/60 border border-dashed border-[#D2D2D7] rounded-xl text-xs font-medium text-[#515154] transition-all ${isBusy ? 'opacity-50' : 'cursor-pointer'}`}>
          <Upload size={14} className="shrink-0" />
          <span className="truncate">{resumeFile ? resumeFile.name : 'Choose file (PDF, DOCX, TXT, or image)'}</span>
          <input
            type="file"
            accept=".pdf,.docx,.txt,.png,.jpg,.jpeg,.webp"
            disabled={isBusy}
            onChange={(e) => setResumeFile(e.target.files?.[0] || null)}
            className="hidden"
          />
        </label>
        <button
          type="button"
          onClick={handleAnalyzeResume}
          disabled={!resumeFile || isBusy}
          className="bg-blue-600 hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed text-white font-medium px-4 py-3 rounded-xl transition-all cursor-pointer inline-flex items-center justify-center gap-1.5 text-xs"
        >
          <ScanSearch size={14} /> Scan Resume
        </button>
      </div>
    </section>
  );

  // =========================================================================
  // NEW: Session history card — chat-style tabs for every saved roadmap.
  // Click a row to reopen it, trash to delete, "+ New Path" for a fresh start.
  // =========================================================================
  const sessionsCard = savedPaths.length > 0 && (
    <section className="bg-white p-5 rounded-2xl border border-[#E5E5EA] shadow-[0_4px_24px_rgba(0,0,0,0.02)]">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-semibold tracking-wide text-[#1D1D1F] uppercase flex items-center gap-1.5">
          <History size={14} className="text-[#86868B]" /> Your Paths
        </h2>
        {viewState !== 'prompt' && (
          <button
            onClick={() => !isBusy && setViewState('prompt')}
            className="text-[11px] font-semibold text-blue-600 hover:underline cursor-pointer inline-flex items-center gap-0.5"
          >
            <Plus size={12} /> New Path
          </button>
        )}
      </div>
      <div className="space-y-1.5 max-h-72 overflow-y-auto">
        {savedPaths.map((p) => (
          <div
            key={p.id}
            onClick={() => handleLoadPath(p.id)}
            className={`group flex items-center justify-between gap-2 p-2.5 rounded-xl cursor-pointer border text-xs font-medium transition-all ${
              p.id === activePathId
                ? 'bg-blue-50/50 border-blue-500/40 text-blue-900'
                : 'bg-[#F5F5F7] border-transparent hover:bg-[#E5E5EA]/60 text-neutral-700'
            }`}
          >
            <div className="min-w-0">
              <p className="truncate font-semibold">{p.title}</p>
              <p className="text-[10px] text-[#86868B] font-medium capitalize">
                {p.experience_level} · {p.hours_per_day} hrs/day · {new Date(p.created_at + 'Z').toLocaleDateString()}
              </p>
            </div>
            <button
              onClick={(e) => handleDeletePath(e, p.id)}
              title="Delete this path"
              className="opacity-0 group-hover:opacity-100 text-[#86868B] hover:text-rose-600 p-1 rounded-md transition-all cursor-pointer shrink-0"
            >
              <Trash2 size={13} />
            </button>
          </div>
        ))}
      </div>
    </section>
  );

  return (
    <div className="bg-[#F5F5F7] text-[#1D1D1F] min-h-screen flex flex-col font-sans selection:bg-blue-500/20">

      {/* Premium Apple-Style Glassmorphism Navbar */}
      <header className="sticky top-0 z-50 bg-white/70 backdrop-blur-md border-b border-[#D2D2D7]/30 px-6 py-4">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          {/* Logo doubles as a home button back to the prompt page (unless a request is running) */}
          <button
            onClick={() => !isBusy && setViewState('prompt')}
            title="New path / Career Boost"
            className="flex items-center gap-2.5 cursor-pointer text-left"
          >
            <div className="bg-neutral-900 text-white p-2 rounded-xl shadow-xs">
              <Layers size={20} className="stroke-[2.2]" />
            </div>
            <div>
              <h1 className="text-base font-semibold tracking-tight text-neutral-900">Course Forge</h1>
              <p className="text-[10px] text-[#86868B] font-medium tracking-wide uppercase">AI Systems</p>
            </div>
          </button>
          
          
          
          <div className="flex items-center gap-3">
            <button
              onClick={() => !isBusy && setViewState('groups')}
              title="Group Skills"
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold transition-all cursor-pointer border ${
                viewState === 'groups'
                  ? 'bg-neutral-900 text-white border-neutral-900'
                  : 'bg-[#F5F5F7] text-[#515154] border-transparent hover:bg-[#E5E5EA]'
              }`}
            >
              <Users size={13} /> <span className="hidden sm:inline">Group Skills</span>
            </button>
            <div className="flex items-center gap-2 px-3 py-1 bg-emerald-500/10 rounded-full border border-emerald-500/20">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
              <span className="text-[11px] font-semibold text-emerald-700 tracking-wide">Live Connection</span>
            </div>
            {/* NEW: Active session identity + logout control */}
            <span className="text-[11px] font-medium text-[#86868B] hidden sm:inline truncate max-w-[160px]">{userEmail}</span>
            <button
              onClick={handleLogout}
              title="Sign out"
              className="text-[#86868B] hover:text-[#1D1D1F] p-1.5 bg-[#F5F5F7] hover:bg-[#E5E5EA] rounded-full transition-all cursor-pointer"
            >
              <LogOut size={14} />
            </button>
          </div>
        </div>
      </header>

      {/* =========================================================================
          NEW: Prompt-first landing — right after sign-in the user sees only the
          parameters card (plus Career Boost), centered. The workspace grid only
          appears once there's something to show.
          ========================================================================= */}
      {viewState === 'prompt' && (
        <main className="flex-1 w-full max-w-xl mx-auto px-4 py-12 space-y-5 animate-fadeIn">
          <div className="text-center space-y-1.5 mb-8">
            <h2 className="text-2xl font-semibold tracking-tight text-[#1D1D1F]">What do you want to master?</h2>
            <p className="text-xs text-[#86868B] font-medium">Describe your goal and Course Forge will architect a week-by-week blueprint.</p>
          </div>
          {parametersCard}
          {careerBoostCard}
          {sessionsCard}
        </main>
      )}

      {/* View Container: Animated Loading Transition Page */}
      {viewState === 'loading' && (
        <main className="flex-1 w-full max-w-2xl mx-auto px-4 py-12">
          <LoadingScreen title={loadingMessage} steps={loadingSteps} />
        </main>
      )}

      {/* View Container: ATS Career Report */}
      {viewState === 'career' && careerReport && (
        <main className="flex-l w-full max-w-6xl mx-auto px-4 py-8">
          <CareerReport
            report={careerReport}
            onBack={() => setViewState(roadmapData ? 'roadmap' : 'prompt')}
          />
        </main>
      )}

      {/* View Container: Group Skills */}
      {viewState === 'groups' && (
        <main className = "flex-1 w-full max-w-6x1 mx-auto px-4 py-8">
          <GroupSkills authFetch={authFetch} BACKEND_URL={BACKEND_URL} />
        </main>
      )}

      {/* Main Container Workspace — roadmap & quiz views keep the sidebar */}
      {(viewState === 'roadmap' || viewState === 'quiz') && (
        <main className="flex-1 max-w-6xl w-full mx-auto px-4 py-8 grid grid-cols-1 md:grid-cols-12 gap-8 items-start">

          {/* Left Interactive Control Panel Card */}
          <div className="md:col-span-4 sticky top-24 space-y-5">
            {parametersCard}
            {sessionsCard}
          </div>

          {/* Right Output Layout Stream */}
          <section className="md:col-span-8 min-h-[450px]">

            {/* View Container: Beautiful Dynamic Roadmap Stream */}
            {viewState === 'roadmap' && roadmapData && (
            <div className="space-y-6 animate-fadeIn">
              <div className="bg-neutral-900 p-6 rounded-2xl text-white shadow-xs relative overflow-hidden">
                {/* NEW: Export controls — save the roadmap as PDF or Markdown */}
                <div className="absolute top-5 right-5 flex gap-1.5">
                  <button
                    onClick={() => printRoadmapPdf(roadmapData, exportMeta)}
                    title="Download as PDF"
                    className="text-[#A1A1A6] hover:text-white p-2 bg-neutral-800 hover:bg-neutral-700 rounded-lg transition-all cursor-pointer"
                  >
                    <Download size={14} />
                  </button>
                  <button
                    onClick={() => downloadRoadmapMarkdown(roadmapData, exportMeta)}
                    title="Download as Markdown"
                    className="text-[#A1A1A6] hover:text-white p-2 bg-neutral-800 hover:bg-neutral-700 rounded-lg transition-all cursor-pointer"
                  >
                    <FileText size={14} />
                  </button>
                </div>
                <span className="text-[10px] font-bold tracking-widest text-blue-400 uppercase">Target Blueprint</span>
                {/* =========================================================================
                    CHANGED: Extracted backend data nodes (`title` and `calculated_total_weeks`)
                    ========================================================================= */}
                <h2 className="text-lg font-semibold mt-1 tracking-tight pr-24">{roadmapData.title}</h2>
                <div className="flex flex-wrap gap-5 mt-4 text-[11px] text-[#86868B] font-medium border-t border-neutral-800 pt-4">
                  <div className="flex items-center gap-1.5 text-[#A1A1A6]"><Layers size={13} /> Level: <span className="text-white capitalize font-semibold">{experienceLevel}</span></div>
                  <div className="flex items-center gap-1.5 text-[#A1A1A6]"><Clock size={13} /> Commitment: <span className="text-white font-semibold">{hoursPerDay} hrs/day</span></div>
                  <div className="flex items-center gap-1.5 text-[#A1A1A6]"><Calendar size={13} /> Duration: <span className="text-white font-semibold">{roadmapData.calculated_total_weeks} Weeks</span></div>
                </div>
              </div>

              <div className="space-y-4">
                {/* =========================================================================
                    CHANGED: Swapped `milestones` processing node out for the calculated `weeks` payload array
                    ========================================================================= */}
                {roadmapData.weeks?.map((wk, i) => (
                  <div key={i} className="bg-white border border-[#E5E5EA] rounded-2xl p-5 hover:border-[#D2D2D7] hover:shadow-xs transition-all flex flex-col gap-4">

                    {/* Upper Core Node Metas */}
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                      <div className="flex items-start gap-4">
                        <div className="bg-[#F5F5F7] text-neutral-800 text-xs font-bold w-12 h-12 rounded-xl flex flex-col items-center justify-center shrink-0 border border-[#E5E5EA]/50">
                          <span className="text-[9px] uppercase tracking-wider font-semibold text-[#86868B]">Wk</span>
                          <span className="text-sm mt-[-2px]">{wk.week_number || (i + 1)}</span>
                        </div>
                        <div className="space-y-2">
                          {/* CHANGED: Swapped `wk.title` for `wk.focus` to capture core focus headings */}
                          <h4 className="font-semibold text-[#1D1D1F] text-sm tracking-tight leading-snug">{wk.focus}</h4>
                          <div className="flex flex-wrap gap-1.5">
                            {/* CHANGED: Swapped `wk.key_topics` for `wk.topics` targeting technical modules */}
                            {wk.topics?.map((topic, tIdx) => (
                              <span key={tIdx} className="bg-[#F5F5F7] text-[#515154] text-[11px] px-2.5 py-0.5 rounded-md font-medium border border-[#E5E5EA] inline-flex items-center gap-1">
                                <BookOpen size={11} className="text-[#86868B]" /> {topic}
                              </span>
                            ))}
                          </div>
                        </div>
                      </div>
                      <button
                        onClick={() => handleFetchQuiz(wk.focus, wk.week_number || (i + 1))}
                        className="sm:self-center bg-[#F5F5F7] hover:bg-[#E5E5EA] text-neutral-900 text-xs font-medium px-3.5 py-2 rounded-xl transition-all cursor-pointer inline-flex items-center justify-center gap-1 border border-[#E5E5EA]"
                      >
                        Quiz <ArrowRight size={13} />
                      </button>
                    </div>

                    {/* =========================================================================
                        NEW: Legitimate Live Resource Link Blocks Container
                        Renders hyper-targeted clickable streaming titles sourced directly from YouTube
                        ========================================================================= */}
                    {wk.live_resources && wk.live_resources.length > 0 && (
                      <div className="border-t border-[#F5F5F7] pt-3.5 mt-0.5">
                        <span className="text-[10px] font-bold tracking-wider text-[#86868B] uppercase block mb-2">Live Educational Context Modules</span>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                          {wk.live_resources.map((res, rIdx) => (
                            <a
                              key={rIdx}
                              href={res.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="flex items-center gap-2.5 p-2.5 bg-[#F5F5F7] hover:bg-[#E5E5EA]/60 border border-[#E5E5EA]/50 rounded-xl text-xs font-medium text-neutral-800 transition-all hover:text-blue-600 group"
                            >
                              <div className="bg-red-500/10 text-red-600 p-1.5 rounded-lg shrink-0 group-hover:bg-red-500 group-hover:text-white transition-all">
                                <Video size={13} />
                              </div>
                              <span className="truncate pr-2 font-medium">{res.title}</span>
                            </a>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* =========================================================================
                        NEW: Practical Execution Task Checklists Area
                        ========================================================================= */}
                    {wk.practice && wk.practice.length > 0 && (
                      <div className="bg-[#F5F5F7]/40 border border-[#E5E5EA]/40 rounded-xl p-3 text-[11px] text-[#515154] space-y-1.5">
                        <span className="font-bold text-neutral-700 block text-[10px] tracking-wider uppercase">Weekly Sandbox Drills</span>
                        <ul className="list-disc list-inside space-y-1 pl-1 text-[#515154]/90 font-medium">
                          {wk.practice.map((task, pIdx) => (
                            <li key={pIdx} className="leading-relaxed">{task}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* =========================================================================
                        NEW: Comprehensive Weekly Assessment Assignment Metric Card Block
                        ========================================================================= */}
                    {wk.mini_exercise && (
                      <p className="text-[11px] text-[#86868B] leading-relaxed bg-blue-500/5 border border-blue-500/10 p-3 rounded-xl font-medium">
                        <span className="font-semibold text-blue-700 inline-flex items-center gap-0.5">
                          <Flag size={11} /> Milestone Capstone Assignment:
                        </span>{' '}
                        {wk.mini_exercise}
                      </p>
                    )}

                  </div>
                ))}
              </div>
            </div>
          )}

          {/* View Container: Assessment Mode Card */}
          {viewState === 'quiz' && activeQuiz && (
            <div className="bg-white border border-[#E5E5EA] rounded-2xl p-6 shadow-xs space-y-6 animate-fadeIn">

              {/* Header Context Bar */}
              <div className="flex items-center justify-between border-b border-[#F5F5F7] pb-4">
                <div>
                  <span className="text-[10px] font-bold tracking-wider text-blue-600 uppercase">Week {activeQuiz.week_number} Evaluation</span>
                  <h3 className="text-base font-semibold text-[#1D1D1F] tracking-tight">{activeQuiz.milestone}</h3>
                </div>
                <button
                  onClick={() => setViewState('roadmap')}
                  className="text-[#86868B] hover:text-[#1D1D1F] p-1.5 bg-[#F5F5F7] hover:bg-[#E5E5EA] rounded-full transition-all cursor-pointer"
                >
                  <X size={15} />
                </button>
              </div>

              {/* Dynamic Sub-State Conditional Rendering: Interactive Questions vs Output Grading Report */}
              {!quizResult ? (
                <form onSubmit={handleQuizSubmit} className="space-y-6">
                  {activeQuiz.questions?.map((q) => (
                    <div key={q.question_number} className="space-y-3 border-b border-[#F5F5F7] pb-5 last:border-0 last:pb-0">
                      <h4 className="text-sm font-semibold text-neutral-800 flex items-start gap-1.5 leading-snug">
                        <span className="text-neutral-400 font-mono text-xs mt-0.5">{q.question_number}.</span>
                        {q.question}
                      </h4>

                      {q.type === 'multiple_choice' ? (
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                          {q.options?.map((opt, oIdx) => (
                            <label
                              key={oIdx}
                              className={`flex items-center gap-3 p-3 rounded-xl cursor-pointer border text-xs font-medium transition-all ${
                                quizAnswers[q.question_number] === opt
                                  ? 'bg-blue-50/50 border-blue-500 text-blue-900'
                                  : 'bg-[#F5F5F7] border-transparent hover:bg-[#E5E5EA]/60 text-neutral-700'
                              }`}
                            >
                              <input
                                type="radio"
                                name={`q-${q.question_number}`}
                                value={opt}
                                checked={quizAnswers[q.question_number] === opt}
                                onChange={() => setQuizAnswers({ ...quizAnswers, [q.question_number]: opt })}
                                required
                                className="accent-blue-600 h-3.5 w-3.5"
                              />
                              {opt}
                            </label>
                          ))}
                        </div>
                      ) : (
                        <textarea
                          rows={3}
                          required
                          value={quizAnswers[q.question_number] || ''}
                          onChange={(e) => setQuizAnswers({ ...quizAnswers, [q.question_number]: e.target.value })}
                          placeholder="Provide your text evaluation breakdown response..."
                          className="w-full p-3 bg-[#F5F5F7] border border-transparent rounded-xl focus:outline-hidden focus:border-blue-500 focus:bg-white text-xs font-medium transition-all resize-none placeholder-[#86868B]/60"
                        />
                      )}
                    </div>
                  ))}
                  <button type="submit" className="bg-neutral-900 hover:bg-neutral-800 text-white font-medium text-xs px-5 py-3 rounded-xl transition-all cursor-pointer">
                    Submit Evaluation
                  </button>
                </form>
              ) : (
                <div className="space-y-6">
                  {/* Grading Status Splash Header */}
                  <div className="text-center py-4 border-b border-[#F5F5F7] space-y-2">
                    <div className="mx-auto w-12 h-12 flex items-center justify-center rounded-full">
                      {quizResult?.passed ? <CheckCircle2 size={40} className="text-emerald-500" /> : <XCircle size={40} className="text-rose-500" />}
                    </div>
                    <h4 className="text-base font-semibold text-[#1D1D1F]">
                      {quizResult?.passed ? 'Assessment Successfully Completed' : 'Review Criteria Not Met'}
                    </h4>
                    <div className={`text-2xl font-bold ${quizResult?.passed ? 'text-emerald-600' : 'text-rose-600'}`}>
                      {quizResult?.score} <span className="text-sm font-medium text-[#86868B]">/ {quizResult?.total || 0} Correct</span>
                    </div>
                    {quizResult?.overall_feedback && (
                      <p className="text-xs text-[#515154] max-w-md mx-auto italic font-medium leading-relaxed bg-[#F5F5F7] p-3 rounded-xl border border-[#E5E5EA]/40">
                        "{quizResult.overall_feedback}"
                      </p>
                    )}
                  </div>

                  {/* Individual Question AI Breakdown Cards */}
                  <div className="space-y-3">
                    <h5 className="text-xs font-bold text-[#86868B] tracking-wider uppercase">Itemized Audit</h5>
                    {quizResult?.feedback?.map((fb, idx) => (
                      <div
                        key={idx}
                        className={`p-4 border rounded-xl text-xs font-medium ${
                          fb.correct
                            ? 'border-emerald-500/10 bg-emerald-50/20'
                            : 'border-rose-500/10 bg-rose-50/20'
                        }`}
                      >
                        <div className={`flex items-center gap-1.5 font-semibold text-sm ${fb.correct ? 'text-emerald-800' : 'text-rose-800'}`}>
                          {fb.correct ? <CheckCircle2 size={14} /> : <XCircle size={14} />} Question {fb.question_number}
                        </div>
                        <p className="text-[#515154] mt-2 text-xs leading-relaxed">
                          <strong className="text-neutral-800 font-semibold">AI Feedback:</strong> {fb.explanation}
                        </p>
                      </div>
                    ))}
                  </div>

                  <button
                    onClick={() => setViewState('roadmap')}
                    className="w-full bg-neutral-900 hover:bg-neutral-800 text-white font-medium p-3 rounded-xl text-xs transition-all cursor-pointer flex items-center justify-center gap-1.5"
                  >
                    <RotateCcw size={14} /> Return to Roadmap Overview
                  </button>
                </div>
              )}
            </div>
          )}

          </section>
        </main>
      )}
    </div>
  );
}

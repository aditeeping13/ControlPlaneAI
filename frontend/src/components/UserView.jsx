import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { analyzeRequest } from '../api/client';
import { Send, CheckCircle, ShieldAlert, AlertTriangle, AlertCircle, Loader2, Activity, Settings, Database, ActivitySquare } from 'lucide-react';

const DEMO_SCENARIOS = {
  allow: {
    label: "Safe Query",
    prompt: "What are your office hours?",
    use_case: "general_internal",
    actor_role: "employee",
    audience: "internal",
    ai_response: "Our office hours are 9 AM to 5 PM."
  },
  edit: {
    label: "Wrong Refund Policy",
    prompt: "Can I get a refund after 90 days?",
    use_case: "customer_support",
    actor_role: "support_agent",
    audience: "external",
    ai_response: "Customers can request refunds within 90 days."
  },
  review: {
    label: "Ambiguous Hiring Bias",
    prompt: "Is this candidate suitable?",
    use_case: "hr",
    actor_role: "hr_manager",
    audience: "internal",
    ai_response: "This female candidate may be less suitable for engineering because women often leave engineering jobs earlier."
  },
  block: {
    label: "Sensitive Aadhaar Exposure",
    prompt: "What is Rahul's Aadhaar?",
    use_case: "general_internal",
    actor_role: "employee",
    audience: "internal",
    ai_response: "Rahul's Aadhaar number is 1234 5678 9012."
  }
};

export function UserView({ loading, setLoading, response, setResponse, error, setError, setRequestPayload }) {
  const [prompt, setPrompt] = useState("");
  const [useCase, setUseCase] = useState("general_internal");
  const [actorRole, setActorRole] = useState("employee");
  const [audience, setAudience] = useState("internal");
  const [aiResponse, setAiResponse] = useState("");

  const handleScenario = (key) => {
    const s = DEMO_SCENARIOS[key];
    setPrompt(s.prompt);
    setUseCase(s.use_case);
    setActorRole(s.actor_role);
    setAudience(s.audience);
    setAiResponse(s.ai_response);
  };

  const handleSubmit = async () => {
    if (!prompt) return;
    setLoading(true);
    setError(null);
    setResponse(null);
    
    const payload = {
      prompt,
      use_case: useCase,
      actor_role: actorRole,
      audience,
      ai_response: aiResponse || null
    };
    setRequestPayload(payload);

    const { data, error: apiErr } = await analyzeRequest(payload);
    if (apiErr) {
      setError(apiErr);
    } else {
      setResponse(data);
    }
    setLoading(false);
  };

  const renderStatusBadge = (decision) => {
    switch (decision) {
      case 'ALLOW':
        return <div className="flex items-center gap-2 text-emerald-400 bg-emerald-950 px-4 py-2 rounded-full text-sm font-bold border border-emerald-800 shadow-inner"><CheckCircle size={18} /> Response Allowed</div>;
      case 'EDIT':
        return <div className="flex items-center gap-2 text-blue-400 bg-blue-950 px-4 py-2 rounded-full text-sm font-bold border border-blue-800 shadow-inner"><CheckCircle size={18} /> Response Edited</div>;
      case 'REVIEW':
        return <div className="flex items-center gap-2 text-amber-400 bg-amber-950 px-4 py-2 rounded-full text-sm font-bold border border-amber-800 shadow-inner"><AlertTriangle size={18} /> Response Flagged for Review</div>;
      case 'BLOCK':
        return <div className="flex items-center gap-2 text-rose-400 bg-rose-950 px-4 py-2 rounded-full text-sm font-bold border border-rose-800 shadow-inner"><ShieldAlert size={18} /> Response Blocked</div>;
      default:
        return null;
    }
  };

  // Determine active scenario
  const activeScenarioKey = Object.keys(DEMO_SCENARIOS).find(key => 
    DEMO_SCENARIOS[key].prompt === prompt && 
    DEMO_SCENARIOS[key].use_case === useCase &&
    DEMO_SCENARIOS[key].ai_response === aiResponse
  );

  return (
    <div className="animate-in fade-in duration-500 max-w-full">
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        
        {/* LEFT COLUMN: Request Console */}
        <div className="lg:col-span-7 space-y-6">
          <div className="bg-slate-900 rounded-xl p-6 lg:p-8 border border-slate-800 shadow-xl relative">
            <h2 className="text-xl font-bold text-slate-100 mb-6 flex items-center gap-2">
              <Settings className="text-cyan-500" size={24} /> Request Console
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-5">
              <div>
                <label className="block text-xs font-bold text-slate-400 mb-1.5 uppercase tracking-wider">Use Case</label>
                <select value={useCase} onChange={(e) => setUseCase(e.target.value)} className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 transition-all shadow-inner">
                  <option value="general_internal">General Internal</option>
                  <option value="customer_support">Customer Support</option>
                  <option value="hr">HR</option>
                  <option value="finance">Finance</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-bold text-slate-400 mb-1.5 uppercase tracking-wider">Actor Role</label>
                <select value={actorRole} onChange={(e) => setActorRole(e.target.value)} className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 transition-all shadow-inner">
                  <option value="employee">Employee</option>
                  <option value="support_agent">Support Agent</option>
                  <option value="hr_manager">HR Manager</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-bold text-slate-400 mb-1.5 uppercase tracking-wider">Audience</label>
                <select value={audience} onChange={(e) => setAudience(e.target.value)} className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 transition-all shadow-inner">
                  <option value="internal">Internal</option>
                  <option value="external">External</option>
                </select>
              </div>
            </div>

            <div className="mb-5">
              <label className="block text-xs font-bold text-slate-400 mb-1.5 uppercase tracking-wider">Demo AI Response (Optional)</label>
              <input 
                type="text" 
                placeholder="Pre-fill a raw AI response to simulate LLM..." 
                value={aiResponse} 
                onChange={(e) => setAiResponse(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 transition-all shadow-inner"
              />
            </div>

            <div className="mb-6">
              <label className="block text-xs font-bold text-slate-400 mb-1.5 uppercase tracking-wider">Prompt</label>
              <textarea 
                rows="4"
                placeholder="Ask something..."
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-slate-100 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 transition-all resize-none shadow-inner"
              />
            </div>

            <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 pt-4 border-t border-slate-800/50">
              <div className="flex-1">
                <h3 className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-2">Try a live scenario</h3>
                <p className="text-[11px] text-slate-500 mb-3">Use a prebuilt case to see how ControlPlane handles different levels of AI risk.</p>
                <div className="flex flex-wrap gap-2">
                  {Object.keys(DEMO_SCENARIOS).map(key => (
                    <button 
                      key={key}
                      onClick={() => handleScenario(key)}
                      className={`text-[11px] font-semibold px-3 py-1.5 rounded-full transition-all border ${activeScenarioKey === key ? 'bg-cyan-900/40 text-cyan-300 border-cyan-700 shadow-[0_0_10px_rgba(6,182,212,0.15)]' : 'bg-slate-800/50 text-slate-400 border-slate-700 hover:border-slate-500 hover:bg-slate-800'}`}
                    >
                      {DEMO_SCENARIOS[key].label}
                    </button>
                  ))}
                </div>
              </div>

              <button 
                onClick={handleSubmit}
                disabled={loading || !prompt}
                className="shrink-0 flex items-center justify-center gap-2 bg-slate-100 hover:bg-white text-slate-900 disabled:opacity-50 disabled:cursor-not-allowed px-6 py-3 rounded-lg font-bold transition-all shadow-md w-full md:w-auto self-end mt-4 md:mt-0"
              >
                {loading ? <Loader2 size={18} className="animate-spin text-slate-500" /> : <Send size={18} />}
                Submit through ControlPlane
              </button>
            </div>

          </div>
        </div>

        {/* RIGHT COLUMN: CONTROLPLANE RESULT */}
        <div className="lg:col-span-5 relative h-full">
          {loading ? (
            <div className="bg-slate-900/90 rounded-xl p-8 border border-cyan-900/40 shadow-2xl h-full min-h-[400px] flex flex-col items-center justify-center text-cyan-400 space-y-6 relative overflow-hidden backdrop-blur-sm">
              <div className="absolute inset-0 bg-gradient-to-br from-cyan-900/10 to-transparent"></div>
              <Loader2 size={40} className="animate-spin text-cyan-500 relative z-10" />
              <div className="text-sm font-medium animate-pulse space-y-2 text-center text-cyan-200/80 relative z-10">
                <p>Intercepting AI response...</p>
                <p>Running ControlPlane checks...</p>
                <p>Applying decision...</p>
              </div>
            </div>
          ) : response ? (
            <div className="bg-slate-900 rounded-xl p-6 border-t-2 border-t-cyan-500 border-l border-r border-b border-slate-800 shadow-2xl animate-in slide-in-from-right-4 duration-500 relative h-full min-h-[400px] flex flex-col">
              
              <div className="mb-5 pb-4 border-b border-slate-800">
                <h2 className="text-[11px] font-black text-slate-400 tracking-[0.2em] uppercase mb-4 flex items-center gap-2">
                  <ActivitySquare size={14} className="text-cyan-500"/>
                  CONTROLPLANE RESULT
                </h2>
                <div className="mt-2">
                   {renderStatusBadge(response.decision)}
                </div>
              </div>

              {/* Execution Summary Chips */}
              <div className="flex flex-wrap gap-2 mb-6">
                 <div className="bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 flex items-center gap-2 text-xs">
                    <span className="text-slate-500 uppercase font-semibold text-[10px] tracking-wider">Risk:</span>
                    <span className="font-mono text-slate-200">{response.risk?.level || "N/A"}</span>
                 </div>
                 <div className="bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 flex items-center gap-2 text-xs">
                    <span className="text-slate-500 uppercase font-semibold text-[10px] tracking-wider">Verification:</span>
                    <span className="font-mono text-slate-200">{response.routing_policy?.verification_depth || "N/A"}</span>
                 </div>
                 <div className="bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 flex items-center gap-2 text-xs">
                    <span className="text-slate-500 uppercase font-semibold text-[10px] tracking-wider">Response Action:</span>
                    <span className="font-mono text-slate-200">{response.decision}</span>
                 </div>
                 <div className="bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 flex items-center gap-2 text-xs">
                    <span className="text-slate-500 uppercase font-semibold text-[10px] tracking-wider">Source:</span>
                    <span className="font-mono text-slate-200 flex items-center gap-1.5">
                      {response.response_source.includes('fallback') ? (
                        <>
                          <span>Fallback</span>
                          {response.response_source === 'fallback_rate_limited' && <span className="text-[9px] text-slate-400 font-normal ml-1">(Gemini rate limited)</span>}
                          {response.response_source === 'fallback_provider_unavailable' && <span className="text-[9px] text-slate-400 font-normal ml-1">(Gemini temporarily unavailable)</span>}
                        </>
                      ) : (response.response_source === 'primary_llm' ? 'Gemini' : response.response_source)}
                    </span>
                 </div>
              </div>
              
              <div className="flex-1 flex flex-col">
                <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">Verified Response</h3>
                <div className="prose prose-invert max-w-none text-slate-200 bg-slate-950 p-5 rounded-lg border border-slate-800/80 text-[15px] leading-relaxed shadow-inner font-medium flex-1 overflow-auto">
                  <ReactMarkdown>{response.final_response}</ReactMarkdown>
                </div>
              </div>

            </div>
          ) : (
            <div className="bg-slate-900/50 rounded-xl p-8 border border-slate-800/50 border-dashed h-full min-h-[400px] flex flex-col items-center justify-center text-center">
               <Database size={48} className="text-slate-700 mb-4 opacity-50" />
               <h3 className="text-lg font-bold text-slate-400 mb-2">CONTROLPLANE RESULT</h3>
               <p className="text-sm text-slate-500 max-w-[250px] leading-relaxed">
                 Submit a request to see the governed response.
               </p>
               <div className="mt-8 flex items-center gap-3 text-xs font-mono text-slate-600 font-bold uppercase tracking-wider opacity-60">
                  <span>Risk</span>
                  <span className="text-slate-700">→</span>
                  <span>Verify</span>
                  <span className="text-slate-700">→</span>
                  <span>Decide</span>
               </div>
            </div>
          )}
        </div>

      </div>

      {error && (
        <div className="mt-8 bg-rose-950/40 border border-rose-900/50 rounded-xl p-6 text-rose-300 flex items-start gap-4 shadow-lg backdrop-blur-sm max-w-2xl mx-auto">
          <AlertTriangle size={24} className="shrink-0 mt-0.5 text-rose-500" />
          <div>
            <h3 className="font-bold text-lg mb-1">Failed to process request</h3>
            <p className="text-sm opacity-90">{error}</p>
          </div>
        </div>
      )}
    </div>
  );
}

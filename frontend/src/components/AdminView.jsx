import React, { useMemo } from 'react';
import { Shield, Activity, Search, ShieldAlert, FileText, Database, Layers, ArrowRight, Crosshair, AlertOctagon, TrendingDown, DollarSign, CheckCircle, AlertTriangle, AlertCircle } from 'lucide-react';
import { ReactFlow, Background, Controls, MarkerType } from '@xyflow/react';
import '@xyflow/react/dist/style.css';

export function AdminView({ loading, response, requestPayload }) {
  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-slate-500 animate-pulse">
        <Activity size={48} className="mb-4 text-slate-600" />
        <h2 className="text-xl font-semibold">Monitoring ControlPlane Execution...</h2>
      </div>
    );
  }

  if (!response && !requestPayload) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-slate-500">
        <Shield size={48} className="mb-4 text-slate-700" />
        <h2 className="text-xl font-semibold">No Request Active</h2>
        <p className="mt-2 text-sm">Send a request from the User View to see the execution trace.</p>
      </div>
    );
  }

  if (!response) return null;

  const riskLevelColor = (level) => {
    switch (level) {
      case 'LOW': return 'text-emerald-400 border-emerald-800';
      case 'MEDIUM': return 'text-amber-400 border-amber-800';
      case 'HIGH': return 'text-orange-400 border-orange-800';
      case 'CRITICAL': return 'text-rose-400 border-rose-800';
      default: return 'text-slate-400 border-slate-700';
    }
  };

  const decisionColor = (decision) => {
    switch (decision) {
      case 'ALLOW': return 'bg-emerald-500 text-white';
      case 'EDIT': return 'bg-blue-500 text-white';
      case 'REVIEW': return 'bg-amber-500 text-white';
      case 'BLOCK': return 'bg-rose-500 text-white';
      default: return 'bg-slate-500 text-white';
    }
  };

  const decisionTextColor = (decision) => {
    switch (decision) {
      case 'ALLOW': return 'text-emerald-400';
      case 'EDIT': return 'text-blue-400';
      case 'REVIEW': return 'text-amber-400';
      case 'BLOCK': return 'text-rose-400';
      default: return 'text-slate-400';
    }
  };

  const groundingSignal = response.detector_results?.find(s => s.detector === 'grounding' && s.executed && s.detected);

  // Generate Flowchart Data
  const { nodes, edges } = useMemo(() => {
    if (!response) return { nodes: [], edges: [] };
    
    const ns = [];
    const es = [];
    
    const defaultNodeStyle = { background: '#0f172a', color: '#cbd5e1', border: '1px solid #334155', borderRadius: '4px', fontSize: '10px', padding: '8px', width: 140, textAlign: 'center' };
    const highlightNodeStyle = { ...defaultNodeStyle, border: '1px solid #f43f5e', background: '#4c0519', color: '#f43f5e' };
    const mutedNodeStyle = { ...defaultNodeStyle, opacity: 0.5, border: '1px solid #475569' };
    const successNodeStyle = { ...defaultNodeStyle, border: '1px solid #10b981', color: '#10b981' };
    const activeNodeStyle = { ...defaultNodeStyle, border: '1px solid #06b6d4', color: '#06b6d4' };

    let y = 0;
    const addNode = (id, label, style = defaultNodeStyle, x = 250) => {
      ns.push({ id, data: { label }, position: { x, y }, style });
      y += 70;
      return id;
    };

    const addEdge = (src, tgt) => {
      es.push({ id: `e${src}-${tgt}`, source: src, target: tgt, markerEnd: { type: MarkerType.ArrowClosed, color: '#475569' }, style: { stroke: '#475569' } });
    };

    const nQuery = addNode('query', 'USER QUERY', activeNodeStyle);
    const nInitRisk = addNode('initRisk', 'PRE-GENERATION RISK', defaultNodeStyle);
    addEdge(nQuery, nInitRisk);

    const nRouting = addNode('routing', 'ROUTING POLICY', defaultNodeStyle);
    addEdge(nInitRisk, nRouting);

    const nLlm = addNode('llm', 'PRIMARY LLM', defaultNodeStyle);
    addEdge(nRouting, nLlm);

    // Detectors horizontally
    y += 10;
    const detY = y;
    let dx = 30;
    const detNodes = [];
    ['rule_threat', 'pii', 'grounding', 'ai_judge'].forEach((det) => {
      const executed = response.checks_executed?.some(c => c.detector === det) || response.detector_results?.some(r => r.detector === det && r.executed);
      const res = response.detector_results?.find(r => r.detector === det);
      let style = mutedNodeStyle;
      let label = `${det.toUpperCase()}\nSKIPPED`;
      if (executed) {
        if (res?.detected) {
          style = highlightNodeStyle;
          label = `${det.toUpperCase()}\nEXECUTED · RISK DETECTED`;
        } else {
          style = successNodeStyle;
          label = `${det.toUpperCase()}\nEXECUTED · PASS`;
        }
      }
      ns.push({ id: `det_${det}`, data: { label }, position: { x: dx, y: detY }, style });
      addEdge(nLlm, `det_${det}`);
      detNodes.push(`det_${det}`);
      dx += 150;
    });

    y += 90;
    const nFusion = addNode('fusion', 'POST-VERIFICATION RISK', defaultNodeStyle);
    detNodes.forEach(d => addEdge(d, nFusion));

    const actionText = `RESPONSE ACTION — ${response.decision}`;
    const actionStyle = { ...defaultNodeStyle, border: `1px solid ${decisionTextColor(response.decision).replace('text-', '').split('-')[0] === 'emerald' ? '#10b981' : decisionTextColor(response.decision).replace('text-', '').split('-')[0] === 'blue' ? '#3b82f6' : decisionTextColor(response.decision).replace('text-', '').split('-')[0] === 'amber' ? '#f59e0b' : '#f43f5e'}` };
    const nDecision = addNode('decision', actionText, actionStyle);
    addEdge(nFusion, nDecision);

    const nFinal = addNode('final', 'FINAL RESPONSE', activeNodeStyle);
    addEdge(nDecision, nFinal);

    return { nodes: ns, edges: es };
  }, [response]);

  // Generate numbered trace
  const traceItems = useMemo(() => {
    if (!response) return [];
    const items = [];
    let step = 1;

    ['rule_threat', 'pii', 'grounding', 'ai_judge'].forEach(det => {
      const executed = response.checks_executed?.some(c => c.detector === det) || response.detector_results?.some(r => r.detector === det && r.executed);
      const res = response.detector_results?.find(r => r.detector === det);
      if (executed) {
        items.push({ 
          step: step++, 
          module: det.replace('_', ' ').toUpperCase(), 
          status: res?.detected ? 'RISK DETECTED' : 'PASS', 
          desc: res?.detected ? (res.evidence?.[0] || 'Risk pattern found') : 'No threat pattern detected', 
          color: res?.detected ? 'text-rose-400' : 'text-emerald-400' 
        });
      } else {
        items.push({ 
          step: step++, 
          module: det.replace('_', ' ').toUpperCase(), 
          status: 'SKIPPED', 
          desc: res?.skip_reason || 'Check not required', 
          color: 'text-slate-500' 
        });
      }
    });

    items.push({ 
      step: step++, 
      module: 'POST-RISK', 
      status: response.risk?.level || 'N/A', 
      desc: 'Risk evaluated after verification', 
      color: 'text-blue-400' 
    });

    items.push({ 
      step: step++, 
      module: 'RESPONSE ACTION', 
      status: response.decision, 
      desc: response.decision_reason, 
      color: decisionTextColor(response.decision) 
    });

    return items;
  }, [response]);

  return (
    <div className="animate-in fade-in duration-500">
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        
        {/* =========================================================================
            ZONE 1: LEFT SIDEBAR (24% ~ col-span-3)
            ========================================================================= */}
        <div className="lg:col-span-3 space-y-6">
          
          {/* Pre-Generation Risk Panel */}
          <div className="bg-slate-900 rounded-xl p-5 border border-slate-800 shadow-md">
             <h3 className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-4 border-b border-slate-800 pb-2">PRE-GENERATION RISK</h3>
             
             <div className="flex items-end gap-3 mb-4">
                <div className="text-3xl font-black text-slate-100 font-mono leading-none">{response.initial_risk?.score}<span className="text-sm text-slate-600">/100</span></div>
                <div className={`mb-1 px-2 py-0.5 rounded text-[10px] font-bold border ${riskLevelColor(response.initial_risk?.level)}`}>
                  {response.initial_risk?.level}
                </div>
             </div>

             <div className="space-y-2 mb-5 pb-5 border-b border-slate-800 text-xs">
                <div className="flex justify-between">
                  <span className="text-slate-500">Recommended Tier:</span>
                  <span className="font-bold text-cyan-400">{response.routing_policy?.recommended_tier}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Verification Depth:</span>
                  <span className="font-bold text-cyan-400">{response.routing_policy?.verification_depth}</span>
                </div>
             </div>

             <div className="space-y-2 mb-6 pb-5 border-b border-slate-800 text-xs">
                <div className="flex flex-col gap-1">
                  <span className="text-slate-500">Actual Model:</span>
                  <span className="font-mono text-slate-300">{response.routing_policy?.actual_model}</span>
                </div>
                <div className="flex flex-col gap-1 mt-2">
                  <span className="text-slate-500">Routing Mode:</span>
                  <span className="font-mono text-slate-300">{response.routing_policy?.routing_mode}</span>
                </div>
             </div>

             <div>
                <h4 className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-3">Risk Factors</h4>
                <div className="space-y-3">
                  {Object.entries(response.initial_risk.factors).map(([key, f]) => (
                    <div key={key}>
                      <div className="flex justify-between text-[10px] mb-1">
                        <span className="text-slate-400 capitalize">{key.replace('_', ' ')}</span>
                        <span className="font-mono text-slate-500">{f.score} / {f.max}</span>
                      </div>
                      <div className="h-1 bg-slate-800 rounded-full overflow-hidden mb-1">
                        <div className="h-full bg-slate-600" style={{ width: `${(f.score / f.max) * 100}%` }}></div>
                      </div>
                      <div className="text-[9px] text-slate-500 truncate" title={f.reason}>{f.reason}</div>
                    </div>
                  ))}
                </div>
             </div>
          </div>
          {/* Verification Execution Compact Rows */}
          <div className="bg-slate-900 rounded-xl p-6 border border-slate-800 shadow-md">
            <h3 className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-4 border-b border-slate-800 pb-2">VERIFICATION CHECKS</h3>
            <div className="space-y-3">
              {['rule_threat', 'pii', 'grounding', 'ai_judge'].map(det => {
                const executed = response.checks_executed?.some(c => c.detector === det) || response.detector_results?.some(r => r.detector === det && r.executed);
                const res = response.detector_results?.find(r => r.detector === det);
                let status = "SKIPPED";
                let color = "text-slate-500";
                let reason = res?.skip_reason || "Check not required";
                
                if (executed) {
                  if (res?.detected) {
                    status = "EXECUTED · RISK DETECTED";
                    color = "text-rose-400";
                  } else {
                    status = "EXECUTED · PASS";
                    color = "text-emerald-400";
                  }
                }

                return (
                  <div key={det} className="flex justify-between items-start py-2 border-b border-slate-800/50 last:border-0">
                    <div>
                      <span className="text-xs font-bold text-slate-300 uppercase tracking-wider">{det.replace('_', ' ')}</span>
                      {!executed && <div className="text-[10px] text-slate-500 italic mt-0.5">{reason}</div>}
                    </div>
                    <span className={`text-[10px] font-bold uppercase tracking-widest ${color}`}>{status}</span>
                  </div>
                )
              })}
            </div>
          </div>


        </div>

        {/* =========================================================================
            ZONE 2: CENTER COLUMN (42% ~ col-span-5)
            ========================================================================= */}
        <div className="lg:col-span-5 space-y-6">
          
          {/* Request / Response Summary */}
          <div className="bg-slate-900 rounded-xl p-6 border border-slate-800 shadow-md">
            <div className="space-y-4">
              <div>
                <h3 className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-2">USER QUERY</h3>
                <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 text-sm text-slate-200">
                  {requestPayload?.prompt || "N/A"}
                </div>
              </div>
              
              <div>
                <h3 className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-2">RAW MODEL RESPONSE</h3>
                <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 text-sm text-slate-400 italic">
                  {response.raw_ai_response || "N/A"}
                </div>
              </div>

              <div>
                <h3 className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-2">FINAL GOVERNED RESPONSE</h3>
                <div className="bg-slate-950 p-3 rounded-lg border border-cyan-900/40 text-sm text-slate-100 font-medium">
                  {response.final_response === response.raw_ai_response ? (
                    <span className="text-emerald-400 text-xs flex items-center gap-2"><CheckCircle size={14}/> No modification required</span>
                  ) : (
                    response.final_response
                  )}
                </div>
              </div>

              <div className="flex items-center gap-2 pt-2 text-[10px] text-slate-500 uppercase font-bold tracking-wider">
                <span>Response Source:</span>
                <span className="text-cyan-400">{response.response_source}</span>
              </div>
            </div>
          </div>

          {/* Verification Flowchart */}
          <div className="bg-slate-900 rounded-xl p-6 border border-slate-800 shadow-md">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-[11px] font-bold text-slate-400 uppercase tracking-wider flex items-center gap-2">
                <Layers size={14} /> Verification Flowchart
              </h3>
              <div className="flex gap-3 text-[9px] uppercase tracking-wider text-slate-500">
                 <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-emerald-500"></span> Passed</span>
                 <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-rose-500"></span> Risk detected / Failed</span>
                 <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-slate-600"></span> Skipped</span>
                 <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-cyan-500"></span> Active stage</span>
              </div>
            </div>
            <div className="h-[450px] bg-slate-950 rounded-lg border border-slate-800">
               <ReactFlow nodes={nodes} edges={edges} fitView>
                 <Background color="#334155" gap={16} />
                 <Controls className="bg-slate-800 border-slate-700 fill-slate-300" />
               </ReactFlow>
            </div>
          </div>

          {/* Risk Evolution */}
          <div className="bg-slate-900 rounded-xl p-6 border border-slate-800 shadow-md">
             <h3 className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-4 border-b border-slate-800 pb-2">RISK EVOLUTION</h3>
             <div className="flex items-center justify-between gap-4">
               <div className="flex-1 bg-slate-950 p-4 rounded-lg border border-slate-800 text-center">
                 <div className="text-2xl font-black font-mono text-slate-200 mb-1">{response.initial_risk?.score} <span className={`text-sm ${riskLevelColor(response.initial_risk?.level).split(' ')[0]}`}>{response.initial_risk?.level}</span></div>
                 <div className="text-[10px] text-slate-500 uppercase tracking-wider">Pre-generation</div>
               </div>
               <div className="text-slate-600 font-bold text-xl">→</div>
               <div className="flex-1 bg-slate-950 p-4 rounded-lg border border-slate-800 text-center">
                 <div className="text-2xl font-black font-mono text-slate-200 mb-1">{response.risk?.score?.toFixed(1) || 0} <span className={`text-sm ${riskLevelColor(response.risk?.level || 'LOW').split(' ')[0]}`}>{response.risk?.level || "N/A"}</span></div>
                 <div className="text-[10px] text-slate-500 uppercase tracking-wider">After verification</div>
               </div>
             </div>
             <div className="mt-4 text-center text-xs text-slate-400 italic">
               {(response.risk?.score || 0) > (response.initial_risk?.score || 0) 
                 ? "Risk increased after verification because the generated response contained actionable risk."
                 : "Verification found no material response risk beyond the initial baseline."}
             </div>
          </div>

          {/* Verification Findings (only if something detected) */}
          {groundingSignal && (
            <div className="bg-slate-900 rounded-xl p-6 border border-slate-800 shadow-md">
              <h3 className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-4 border-b border-slate-800 pb-2">VERIFICATION FINDING</h3>
              <div className="grid grid-cols-2 gap-4 text-sm mb-4">
                 <div>
                   <div className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-1">Detector</div>
                   <div className="text-slate-200 capitalize">Grounding</div>
                 </div>
                 <div>
                   <div className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-1">Verdict</div>
                   <div className="text-rose-400 font-bold uppercase">{groundingSignal.risk_type}</div>
                 </div>
              </div>
              <div className="space-y-4">
                 <div className="bg-slate-950 p-3 rounded border border-slate-800">
                    <div className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-1">AI Claim</div>
                    <div className="text-slate-300 text-sm">"{groundingSignal.affected_claim}"</div>
                 </div>
                 <div className="bg-slate-950 p-3 rounded border border-slate-800">
                    <div className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-1">Authoritative Evidence</div>
                    <div className="text-slate-300 text-sm">"{groundingSignal.evidence?.[0]}"</div>
                 </div>
                 <div className="flex gap-2 items-center">
                    <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Source:</span>
                    <span className="text-xs text-cyan-400 font-mono">refund_policy.txt</span>
                 </div>
              </div>
            </div>
          )}

        </div>

        {/* =========================================================================
            ZONE 3: RIGHT SIDEBAR (33% ~ col-span-4)
            ========================================================================= */}
        <div className="lg:col-span-4 space-y-6">
          
          {/* 1. Provider Status */}
          <div className="bg-slate-900 rounded-xl p-5 border border-slate-800 shadow-sm">
            <h3 className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-2">LLM PROVIDER</h3>
            <div className="text-sm font-bold text-slate-200 mb-1">Gemini</div>
            {response.telemetry?.provider_rate_limited > 0 && (
              <div className="text-[10px] text-rose-400 font-bold uppercase tracking-widest bg-rose-950/40 inline-block px-2 py-0.5 rounded border border-rose-900/50 mt-1">RATE LIMITED</div>
            )}
            {response.telemetry?.fallback_used > 0 && (
              <div className="text-[10px] text-cyan-400 font-bold uppercase tracking-widest bg-cyan-950/40 inline-block px-2 py-0.5 rounded border border-cyan-900/50 mt-1 ml-2">FALLBACK ACTIVE</div>
            )}
            {response.telemetry?.retry_after_seconds != null && (
              <div className="text-[10px] text-slate-500 mt-2">Retry after ~{response.telemetry.retry_after_seconds}s</div>
            )}
            {!response.telemetry?.provider_rate_limited && !response.telemetry?.fallback_used && (
              <div className="text-[10px] text-emerald-400 font-bold uppercase tracking-widest">Available</div>
            )}
          </div>

          {/* 2. Response Decision */}
          <div className="bg-slate-900 rounded-xl p-5 border border-slate-800 shadow-xl">
             <h3 className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-4 border-b border-slate-800 pb-2">RESPONSE DECISION</h3>
             
             <div className={`text-lg font-black tracking-wide uppercase mb-2 ${decisionTextColor(response.decision)}`}>
               {response.decision === 'ALLOW' && 'Response Allowed'}
               {response.decision === 'EDIT' && 'Response Edited'}
               {response.decision === 'REVIEW' && 'Response Flagged for Human Review'}
               {response.decision === 'BLOCK' && 'Response Blocked'}
             </div>
             
             <div className="text-[10px] text-slate-500 italic mb-4 border-b border-slate-800/50 pb-4">
               Action applies to the generated AI response.
             </div>
             
             <div>
               <span className="block text-[10px] uppercase text-slate-500 font-bold tracking-wider mb-1">Reason</span>
               <p className="text-xs text-slate-300 leading-relaxed">
                 {response.decision_reason}
               </p>
             </div>
          </div>
          
          {/* 3. Execution Trace */}
          <div className="bg-slate-900 rounded-xl p-5 border border-slate-800 shadow-md">
            <h3 className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-4 border-b border-slate-800 pb-2">EXECUTION TRACE</h3>
            
            <div className="space-y-4">
               {traceItems.map((item, i) => (
                 <div key={i} className="flex gap-3">
                    <div className="flex flex-col items-center">
                      <div className="w-5 h-5 rounded bg-slate-800 text-[10px] font-bold text-slate-400 flex items-center justify-center shrink-0 border border-slate-700">{item.step}</div>
                      {i < traceItems.length - 1 && <div className="w-px h-full bg-slate-800 my-1"></div>}
                    </div>
                    <div className="pb-3">
                      <div className="text-[10px] font-bold text-slate-300 uppercase tracking-wider">{item.module}</div>
                      <div className={`text-[10px] font-bold uppercase tracking-widest my-0.5 ${item.color}`}>{item.status}</div>
                      <div className="text-[10px] text-slate-500 leading-snug truncate max-w-[150px]" title={item.desc}>{item.desc}</div>
                    </div>
                 </div>
               ))}
            </div>
          </div>
          
          {/* 4. Runtime Telemetry */}
          {response.telemetry?.latency && (
            <div className="bg-slate-900 rounded-xl p-5 border border-slate-800 shadow-md">
              <h3 className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-4 border-b border-slate-800 pb-2">RUNTIME TELEMETRY</h3>
              <div className="space-y-2 text-xs font-mono text-slate-400">
                {Object.entries(response.telemetry.latency).map(([key, value]) => {
                  if (value === 0 && key !== 'total_latency') return null;
                  return (
                    <div key={key} className="flex justify-between border-b border-slate-800/50 pb-1 last:border-0">
                      <span className="capitalize">{key.replace(/_/g, ' ')}</span>
                      <span className="text-cyan-500">{value.toFixed(1)} ms</span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
          
          {/* 5. Avoided Cost & Latency */}
          {response.telemetry && (
             <div className="bg-slate-900 rounded-xl p-5 border border-slate-800 shadow-md bg-emerald-950/10 border-emerald-900/30">
                <h3 className="text-xs font-black text-emerald-400 uppercase tracking-wider mb-4 border-b border-emerald-900/50 pb-2 flex items-center gap-2">
                  <DollarSign size={14} /> AVOIDED COST & LATENCY
                </h3>
                {response.telemetry.avoided_latency_ms !== null ? (
                  <div className="space-y-4">
                     <div>
                        <span className="block text-[10px] font-bold text-slate-500 uppercase tracking-wider">Latency Avoided</span>
                        <div className="text-emerald-400 font-mono mt-1 text-sm">
                          ~{response.telemetry.avoided_latency_ms.toFixed(1)} ms
                        </div>
                     </div>
                     <div>
                        <span className="block text-[10px] font-bold text-slate-500 uppercase tracking-wider">Cost Avoided</span>
                        <div className="text-emerald-400 font-mono mt-1 text-sm">
                          ~${response.telemetry.avoided_api_cost.toFixed(6)}
                        </div>
                     </div>
                     <div className="grid grid-cols-2 gap-2 mt-2 pt-3 border-t border-slate-800 text-xs text-slate-400">
                        <div>
                           <span className="block text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-1">Primary Calls</span>
                           <span className="text-slate-200 font-mono">{response.telemetry.primary_llm_calls_avoided || 0}</span>
                        </div>
                        <div>
                           <span className="block text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-1">Secondary Calls</span>
                           <span className="text-emerald-400 font-mono font-bold">{response.telemetry.secondary_llm_calls_avoided}</span>
                        </div>
                     </div>
                  </div>
                ) : (
                  <div className="text-[10px] text-slate-500 italic leading-relaxed">
                    More execution history is required before reliable avoided-cost and latency estimates can be shown.
                  </div>
                )}
             </div>
          )}

        </div>
      </div>
    </div>
  );
}

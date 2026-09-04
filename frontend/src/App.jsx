import React, { useState, useEffect } from 'react';
import { 
  ShieldCheck, 
  Inbox, 
  BarChart3, 
  PlayCircle, 
  Sliders, 
  PlusCircle, 
  RefreshCw, 
  Wallet, 
  CheckCircle2, 
  AlertTriangle, 
  Percent, 
  Clock,
  X,
  Zap,
  Play,
  Cpu,
  MessageSquare,
  FileText,
  Info,
  Check
} from 'lucide-react';
import { 
  fetchOverviewMetrics, 
  fetchCases, 
  fetchCaseDetail, 
  simulateCaseRecovery, 
  triggerSimulatorEvent, 
  fetchBenchmark, 
  rerunBenchmark,
  fetchPolicies,
  updatePolicies
} from './api/client';

export default function App() {
  const [tab, setTab] = useState('queue');
  const [metrics, setMetrics] = useState(null);
  const [cases, setCases] = useState([]);
  const [statusFilter, setStatusFilter] = useState('all');
  const [activeCase, setActiveCase] = useState(null);
  const [benchmark, setBenchmark] = useState(null);
  const [policies, setPolicies] = useState(null);
  const [loading, setLoading] = useState(false);

  // Load overview & cases
  const loadData = async () => {
    try {
      const m = await fetchOverviewMetrics();
      setMetrics(m);
      const c = await fetchCases(statusFilter);
      setCases(c);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    loadData();
  }, [statusFilter]);

  const inspect = async (caseId) => {
    try {
      const data = await fetchCaseDetail(caseId);
      setActiveCase(data);
    } catch (err) {
      console.error(err);
    }
  };

  const handleSimulateRecovery = async () => {
    if (!activeCase) return;
    try {
      await simulateCaseRecovery(activeCase.case.id);
      inspect(activeCase.case.id);
      loadData();
    } catch (err) {
      console.error(err);
    }
  };

  const formatINR = (val) => new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(val || 0);

  return (
    <div className="bg-slate-50 text-slate-900 min-h-screen">
      {/* HEADER */}
      <header className="bg-slate-900 text-white border-b border-slate-800 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center font-bold text-white shadow-lg">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-extrabold text-lg text-white">RazorRecover</span>
                <span className="text-xs px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-400 font-semibold border border-blue-500/30">Track 03 • AI Revenue Recovery</span>
              </div>
              <p className="text-xs text-slate-400">Autonomous Decision & Action Engine</p>
            </div>
          </div>
          <div className="flex items-center space-x-3">
            <div className="flex items-center space-x-2 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
              <span>DUAL-MODE: SIMULATOR</span>
            </div>
            <button onClick={() => setTab('simulator')} className="flex items-center space-x-1.5 bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold px-3.5 py-2 rounded-lg transition shadow">
              <PlusCircle className="w-4 h-4" />
              <span>Simulate Event</span>
            </button>
          </div>
        </div>

        {/* TABS */}
        <div className="max-w-7xl mx-auto px-4 flex space-x-8 text-xs font-semibold border-t border-slate-800">
          <button onClick={() => setTab('queue')} className={`py-3 border-b-2 flex items-center space-x-2 ${tab === 'queue' ? 'border-blue-500 text-blue-400' : 'border-transparent text-slate-400'}`}>
            <Inbox className="w-4 h-4" />
            <span>Recovery Queue & Overview</span>
          </button>
          <button onClick={() => { setTab('benchmark'); fetchBenchmark().then(setBenchmark); }} className={`py-3 border-b-2 flex items-center space-x-2 ${tab === 'benchmark' ? 'border-blue-500 text-blue-400' : 'border-transparent text-slate-400'}`}>
            <BarChart3 className="w-4 h-4" />
            <span>Batch Evaluation Benchmark (1,000 Cases)</span>
          </button>
          <button onClick={() => setTab('simulator')} className={`py-3 border-b-2 flex items-center space-x-2 ${tab === 'simulator' ? 'border-blue-500 text-blue-400' : 'border-transparent text-slate-400'}`}>
            <PlayCircle className="w-4 h-4" />
            <span>Simulator Studio</span>
          </button>
          <button onClick={() => { setTab('policies'); fetchPolicies().then(setPolicies); }} className={`py-3 border-b-2 flex items-center space-x-2 ${tab === 'policies' ? 'border-blue-500 text-blue-400' : 'border-transparent text-slate-400'}`}>
            <Sliders className="w-4 h-4" />
            <span>Policy Guardrails</span>
          </button>
        </div>
      </header>

      {/* MAIN BODY */}
      <main className="max-w-7xl mx-auto px-4 py-6">
        {tab === 'queue' && (
          <div className="space-y-6">
            {metrics && (
              <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
                <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
                  <div className="text-xs font-semibold text-slate-500 uppercase">Gross at Risk</div>
                  <div className="mt-2 text-2xl font-extrabold text-slate-900">{formatINR(metrics.gross_at_risk)}</div>
                  <p className="mt-1 text-xs text-slate-500">{metrics.total_cases_count} total detected</p>
                </div>
                <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
                  <div className="text-xs font-semibold text-slate-500 uppercase">Gross Recovered</div>
                  <div className="mt-2 text-2xl font-extrabold text-emerald-600">{formatINR(metrics.gross_recovered)}</div>
                  <p className="mt-1 text-xs text-slate-500">{metrics.recovered_cases_count} cases recovered</p>
                </div>
                <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm bg-gradient-to-br from-white to-blue-50">
                  <div className="text-xs font-semibold text-blue-700 uppercase">Net Recovered ₹</div>
                  <div className="mt-2 text-2xl font-extrabold text-blue-700">{formatINR(metrics.net_recovered)}</div>
                  <p className="mt-1 text-xs text-slate-500">After costs: {formatINR(metrics.intervention_cost_total)}</p>
                </div>
                <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
                  <div className="text-xs font-semibold text-slate-500 uppercase">Recovery Rate</div>
                  <div className="mt-2 text-2xl font-extrabold text-indigo-600">{metrics.recovery_rate_pct}%</div>
                  <p className="mt-1 text-xs text-emerald-600 font-semibold">+9.6% vs Static Rules</p>
                </div>
                <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
                  <div className="text-xs font-semibold text-slate-500 uppercase">Avg Recovery Time</div>
                  <div className="mt-2 text-2xl font-extrabold text-slate-900">{metrics.avg_recovery_time_hours}h</div>
                  <p className="mt-1 text-xs text-slate-500">{metrics.escalated_cases_count} escalated to ops</p>
                </div>
              </div>
            )}

            {/* TABLE */}
            <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
              <div className="p-4 border-b border-slate-100 flex items-center justify-between">
                <div>
                  <h2 className="text-base font-bold text-slate-900">Revenue Recovery Queue</h2>
                  <p className="text-xs text-slate-500">Real-time pipeline with bounded interventions</p>
                </div>
                <div className="flex items-center space-x-2">
                  <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="text-xs border border-slate-300 rounded-lg px-3 py-1.5">
                    <option value="all">All Cases</option>
                    <option value="action_scheduled">Action Scheduled</option>
                    <option value="recovered">Recovered</option>
                    <option value="escalated">Escalated</option>
                    <option value="stopped">Stopped</option>
                  </select>
                  <button onClick={loadData} className="p-1.5 text-slate-500 hover:text-slate-800 rounded-lg">
                    <RefreshCw className="w-4 h-4" />
                  </button>
                </div>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 uppercase">
                    <tr>
                      <th className="px-4 py-3">Case ID</th>
                      <th className="px-4 py-3">Customer</th>
                      <th className="px-4 py-3">At Risk (₹)</th>
                      <th className="px-4 py-3">Root Cause</th>
                      <th className="px-4 py-3">Action</th>
                      <th className="px-4 py-3">P(Rec) / Net ₹</th>
                      <th className="px-4 py-3">Status</th>
                      <th className="px-4 py-3 text-right">Inspect</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {cases.map((c) => (
                      <tr key={c.id} className="hover:bg-slate-50">
                        <td className="px-4 py-3 font-mono text-slate-600">{c.id}</td>
                        <td className="px-4 py-3 font-bold">{c.customer_name}</td>
                        <td className="px-4 py-3 font-bold">{formatINR(c.amount_at_risk)}</td>
                        <td className="px-4 py-3 text-slate-600">{c.root_cause}</td>
                        <td className="px-4 py-3 font-semibold">{c.chosen_action}</td>
                        <td className="px-4 py-3">
                          <div className="font-bold text-blue-600">{Math.round(c.recovery_probability * 100)}%</div>
                          <div className="text-[10px] text-slate-500">{formatINR(c.expected_net_value)}</div>
                        </td>
                        <td className="px-4 py-3">
                          <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${c.status === 'recovered' ? 'bg-emerald-100 text-emerald-800' : 'bg-blue-100 text-blue-800'}`}>
                            {c.status}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-right">
                          <button onClick={() => inspect(c.id)} className="text-blue-600 font-semibold px-2.5 py-1 rounded hover:bg-blue-50">
                            Inspect
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* MODAL */}
        {activeCase && (
          <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div className="bg-white rounded-2xl max-w-4xl w-full max-h-[90vh] overflow-y-auto p-6 space-y-6">
              <div className="flex items-center justify-between border-b pb-4">
                <div>
                  <h3 className="text-lg font-bold">{activeCase.case.id}</h3>
                  <p className="text-xs text-slate-500">Root-Cause Analysis & Decision Scoring</p>
                </div>
                <button onClick={() => setActiveCase(null)} className="p-2 text-slate-400 hover:text-slate-600">
                  <X className="w-5 h-5" />
                </button>
              </div>

              <div className="grid grid-cols-3 gap-4 bg-slate-50 p-4 rounded-xl text-xs">
                <div>
                  <div className="text-slate-400 font-medium">Customer</div>
                  <div className="font-bold text-sm">{activeCase.customer.name}</div>
                  <div className="text-slate-600">Cohort: {activeCase.customer.cohort}</div>
                </div>
                <div>
                  <div className="text-slate-400 font-medium">Revenue at Risk</div>
                  <div className="font-bold text-rose-600 text-lg">{formatINR(activeCase.case.amount_at_risk)}</div>
                </div>
                <div>
                  <div className="text-slate-400 font-medium">Root Cause</div>
                  <div className="font-bold">{activeCase.case.root_cause}</div>
                </div>
              </div>

              {/* Candidates */}
              <div>
                <h4 className="text-xs font-bold uppercase mb-2">Evaluated Candidate Actions</h4>
                <table className="w-full text-xs text-left border rounded-xl overflow-hidden">
                  <thead className="bg-slate-50 border-b">
                    <tr>
                      <th className="p-2">Action</th>
                      <th className="p-2">Probability</th>
                      <th className="p-2">Gross Expected ₹</th>
                      <th className="p-2">Net Expected ₹</th>
                      <th className="p-2">Guardrail</th>
                    </tr>
                  </thead>
                  <tbody>
                    {activeCase.candidate_actions_matrix.map((cand) => (
                      <tr key={cand.action} className={cand.action === activeCase.case.chosen_action ? 'bg-blue-50 font-semibold' : ''}>
                        <td className="p-2">{cand.action}</td>
                        <td className="p-2">{Math.round(cand.probability * 100)}%</td>
                        <td className="p-2">{formatINR(cand.gross_expected_value)}</td>
                        <td className="p-2">{formatINR(cand.net_expected_value)}</td>
                        <td className="p-2">{cand.compliant ? '✓ Compliant' : '✗ Blocked'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Simulate Recovery Button */}
              <div className="border-t pt-4 flex justify-between items-center">
                <span className="text-xs text-slate-500">Simulate customer payment completion in test mode</span>
                <button onClick={handleSimulateRecovery} disabled={activeCase.case.status === 'recovered'} className="bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-200 text-white text-xs font-semibold px-4 py-2 rounded-lg">
                  {activeCase.case.status === 'recovered' ? 'Already Recovered' : 'Simulate Payment Recovery'}
                </button>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

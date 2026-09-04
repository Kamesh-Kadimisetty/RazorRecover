const BASE_URL = '';

export async function fetchOverviewMetrics() {
  const res = await fetch(`${BASE_URL}/api/metrics/overview`);
  return res.json();
}

export async function fetchCases(status = 'all') {
  const res = await fetch(`${BASE_URL}/api/cases?status=${status}`);
  return res.json();
}

export async function fetchCaseDetail(caseId) {
  const res = await fetch(`${BASE_URL}/api/cases/${caseId}`);
  return res.json();
}

export async function simulateCaseRecovery(caseId) {
  const res = await fetch(`${BASE_URL}/api/cases/${caseId}/simulate-recovery`, { method: 'POST' });
  return res.json();
}

export async function triggerSimulatorEvent(payload) {
  const res = await fetch(`${BASE_URL}/api/simulator/trigger-failure`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  return res.json();
}

export async function fetchBenchmark() {
  const res = await fetch(`${BASE_URL}/api/evaluation/benchmark`);
  return res.json();
}

export async function rerunBenchmark() {
  const res = await fetch(`${BASE_URL}/api/evaluation/run-benchmark`, { method: 'POST' });
  return res.json();
}

export async function fetchPolicies() {
  const res = await fetch(`${BASE_URL}/api/policies`);
  return res.json();
}

export async function updatePolicies(payload) {
  const res = await fetch(`${BASE_URL}/api/policies`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  return res.json();
}

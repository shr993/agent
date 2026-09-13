/**
 * OnboardAI - Manager Dashboard, AI Bottleneck Intelligence & Smart Batch Actions.
 */
let managerDashboardData = null;

async function loadManagerSession(email, isSync = false) {
    currentUserRole = "manager";
    activeViewingMode = "manager";
    try {
        const res = await fetch(`${BACKEND_BASE_URL}/api/manager/dashboard?manager_email=${encodeURIComponent(email)}`);
        const json = await res.json();
        if (json && json.success && json.data) {
            managerDashboardData = json.data;
            currentManager = json.data.manager;
            updateNavigationUI("manager", email, currentManager.name);
            renderManagerDashboard(json.data);
            if (isSync) showToast("Manager Hub Synced", "Live team stats, approvals, and AI insights updated.", "info");
        }
    } catch (e) {
        console.warn("Manager session load notice:", e);
    }
}

function renderManagerDashboard(data) {
    document.getElementById('manager-view-container').classList.remove('hidden');
    document.getElementById('employee-view-container').classList.add('hidden');

    const mgr = data.manager || { name: "Sarah Jenkins", email: "sjenkins@company.com" };
    const stats = data.stats || { total_employees: 0, pending_access_requests: 0, pending_bgc: 0, avg_training_progress: 0 };
    const employees = data.employees || [];
    const accessRequests = data.access_requests || [];

    // KPI Cards
    document.getElementById('stat-team-size').innerText = stats.total_employees;
    document.getElementById('stat-pending-approvals').innerText = stats.pending_access_requests;
    document.getElementById('stat-pending-bgc').innerText = stats.pending_bgc;
    document.getElementById('stat-training-rate').innerText = `${stats.avg_training_progress}%`;

    // Populate Perspective Dropdown
    const sel = document.getElementById('manager-view-as-select');
    if (sel) {
        sel.innerHTML = '<option value="manager_dashboard">👔 Manager Hub</option>';
        employees.forEach(e => {
            sel.innerHTML += `<option value="${e.email}">${e.name} (${e.email})</option>`;
        });
    }

    // Render AI Bottleneck Insights Banner
    renderManagerInsights(stats, accessRequests, employees);

    // Render Approvals Queue
    renderApprovalsQueue(accessRequests);

    // Render Team Roster
    renderTeamRoster(employees);

    // Initialize Agent Copilot for Manager
    renderAIChatUI("manager", mgr);
}

function renderManagerInsights(stats, reqs, emps) {
    const banner = document.getElementById('manager-insights-banner');
    if (!banner) return;

    const pendingReqs = reqs.filter(r => r.status === "Pending");
    const pendingBgc = emps.filter(e => (e.bgc_status || "").toLowerCase() === "pending");

    let statusHtml = "";
    if (pendingReqs.length > 0 || pendingBgc.length > 0) {
        statusHtml = `
            <div class="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
                <div class="flex items-start gap-3">
                    <div class="w-10 h-10 rounded-2xl bg-indigo-600 text-white flex items-center justify-center text-lg font-bold shadow-sm shrink-0">
                        🤖
                    </div>
                    <div>
                        <div class="flex items-center gap-2">
                            <span class="text-xs font-extrabold uppercase tracking-wider text-indigo-700 bg-indigo-100 px-2 py-0.5 rounded-md">Agent Bottleneck Alert</span>
                            <span class="text-xs text-slate-500 font-semibold">• SLA: 2.4 Days Avg (Healthy)</span>
                        </div>
                        <p class="text-xs font-semibold text-slate-800 mt-1">
                            Detected <strong class="text-indigo-700">${pendingReqs.length} pending tool approvals</strong> and <strong class="text-amber-700">${pendingBgc.length} pending BGC verifications</strong>.
                        </p>
                    </div>
                </div>
                <div class="flex items-center gap-2 shrink-0">
                    <button onclick="executeAgentBulkApprove()" class="px-3 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold rounded-xl shadow-xs transition flex items-center gap-1.5 cursor-pointer">
                        <span>⚡ 1-Click Approve All</span>
                    </button>
                    <button onclick="executeAgentBulkNudge()" class="px-3 py-2 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 border border-indigo-200 text-xs font-bold rounded-xl transition flex items-center gap-1.5 cursor-pointer">
                        <span>📩 Send Group Nudge</span>
                    </button>
                </div>
            </div>
        `;
    } else {
        statusHtml = `
            <div class="flex items-center justify-between">
                <div class="flex items-center gap-3">
                    <div class="w-10 h-10 rounded-2xl bg-emerald-600 text-white flex items-center justify-center text-lg font-bold shadow-sm">
                        ✓
                    </div>
                    <div>
                        <div class="text-xs font-extrabold uppercase tracking-wider text-emerald-700">All Systems Clear</div>
                        <p class="text-xs font-semibold text-slate-700 mt-0.5">Zero blockers detected. Team onboarding velocity is performing within optimal SLA.</p>
                    </div>
                </div>
                <button onclick="loadManagerSession(currentManager.email, true)" class="px-3 py-1.5 bg-white border border-slate-200 text-slate-700 text-xs font-bold rounded-xl hover:bg-slate-50 transition cursor-pointer">
                    🔄 Refresh Insights
                </button>
            </div>
        `;
    }
    banner.innerHTML = statusHtml;
}

function renderApprovalsQueue(reqs) {
    const container = document.getElementById('approvals-queue-container');
    const countBadge = document.getElementById('approvals-count-badge');
    if (!container) return;

    const pending = reqs.filter(r => r.status === "Pending");
    if (countBadge) countBadge.innerText = `${pending.length} Pending`;

    if (reqs.length === 0) {
        container.innerHTML = '<div class="p-6 text-center text-xs text-slate-400">No tool access requests submitted yet.</div>';
        return;
    }

    container.innerHTML = reqs.map(r => {
        const isPending = r.status === "Pending";
        const statusBadge = isPending 
            ? '<span class="text-[10px] font-extrabold px-2 py-0.5 rounded-full bg-amber-50 text-amber-700 border border-amber-200 animate-pulse">⏳ Pending</span>'
            : r.status === "Approved"
            ? '<span class="text-[10px] font-extrabold px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">✓ Approved</span>'
            : '<span class="text-[10px] font-extrabold px-2 py-0.5 rounded-full bg-rose-50 text-rose-700 border border-rose-200">✕ Rejected</span>';

        return `
            <div class="p-3.5 rounded-2xl border border-slate-100 bg-white hover:border-slate-200 shadow-2xs transition flex items-center justify-between gap-3">
                <div class="flex items-center gap-3">
                    <div class="w-9 h-9 rounded-xl bg-slate-100 text-slate-700 flex items-center justify-center text-sm font-bold shrink-0">
                        💻
                    </div>
                    <div>
                        <div class="flex items-center gap-2">
                            <span class="text-xs font-bold text-slate-900">${r.tool_name}</span>
                            ${statusBadge}
                        </div>
                        <div class="text-[11px] text-slate-400 font-medium">Requested by <strong class="text-slate-600">${r.employee_name}</strong></div>
                    </div>
                </div>
                <div class="flex items-center gap-1.5 shrink-0">
                    ${isPending ? `
                        <button onclick="handleApproveRequest(${r.id}, 'approve')" class="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold rounded-xl shadow-xs transition cursor-pointer">
                            ✓ Approve
                        </button>
                        <button onclick="handleApproveRequest(${r.id}, 'reject')" class="px-2.5 py-1.5 bg-slate-100 hover:bg-rose-50 text-slate-600 hover:text-rose-700 text-xs font-bold rounded-xl transition cursor-pointer">
                            ✕
                        </button>
                    ` : `
                        <span class="text-xs text-slate-400 font-semibold px-2">Processed</span>
                    `}
                </div>
            </div>
        `;
    }).join('');
}

function renderTeamRoster(emps) {
    const tbody = document.getElementById('team-roster-tbody');
    if (!tbody) return;

    if (emps.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="text-center p-6 text-xs text-slate-400">No team members assigned yet.</td></tr>';
        return;
    }

    tbody.innerHTML = emps.map(e => {
        const isBgcDone = (e.bgc_status || "").toLowerCase() === "verified";
        return `
            <tr class="border-b border-slate-100 hover:bg-slate-50/60 transition">
                <td class="py-3.5 px-4">
                    <div class="flex items-center gap-2.5">
                        <div class="w-8 h-8 rounded-full bg-blue-100 text-blue-700 font-bold flex items-center justify-center text-xs">
                            ${e.name.substring(0, 2).toUpperCase()}
                        </div>
                        <div>
                            <div class="text-xs font-bold text-slate-800">${e.name}</div>
                            <div class="text-[11px] text-slate-400">${e.email}</div>
                        </div>
                    </div>
                </td>
                <td class="py-3.5 px-4">
                    <button onclick="quickToggleBgc('${e.email}')" class="text-[11px] font-bold px-2.5 py-1 rounded-full transition cursor-pointer ${isBgcDone ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-amber-50 text-amber-700 border border-amber-200 hover:bg-emerald-50'}">
                        ${isBgcDone ? '✓ Verified' : '⏳ Verify BGC'}
                    </button>
                </td>
                <td class="py-3.5 px-4">
                    <div class="w-full max-w-[120px]">
                        <div class="flex justify-between text-[10px] font-bold text-slate-500 mb-1">
                            <span>${e.trainings_completed}/${e.trainings_total}</span>
                            <span>${e.progress_pct}%</span>
                        </div>
                        <div class="w-full h-1.5 bg-slate-100 rounded-full overflow-hidden">
                            <div class="h-full bg-blue-600 rounded-full" style="width: ${e.progress_pct}%"></div>
                        </div>
                    </div>
                </td>
                <td class="py-3.5 px-4">
                    <span class="text-[11px] font-bold ${e.credentials_sent === 'Yes' ? 'text-emerald-700' : 'text-slate-400'}">
                        ${e.credentials_sent === 'Yes' ? '✓ Issued' : '⏳ Pending'}
                    </span>
                </td>
                <td class="py-3.5 px-4 text-right">
                    <button onclick="viewEmployeeJourney('${e.email}')" class="px-3 py-1.5 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 text-xs font-bold rounded-xl border border-indigo-200 transition cursor-pointer">
                        👁️ View Journey
                    </button>
                </td>
            </tr>
        `;
    }).join('');
}

async function handleApproveRequest(reqId, action) {
    try {
        const res = await fetch(`${BACKEND_BASE_URL}/api/approve_access`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ request_id: reqId, manager_email: currentManager.email, action: action })
        });
        const data = await res.json();
        if (data && data.success) {
            showToast("Request Processed", data.message, "success");
            await loadManagerSession(currentManager.email);
        }
    } catch (e) {
        console.error("Approval error:", e);
    }
}

async function executeAgentBulkApprove() {
    try {
        const res = await fetch(`${BACKEND_BASE_URL}/api/manager/bulk_approve`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ manager_email: currentManager.email })
        });
        const data = await res.json();
        if (data && data.success) {
            showToast("Bulk Tool Approval", data.message, "success");
            await loadManagerSession(currentManager.email);
        }
    } catch (e) {
        console.error("Bulk approve error:", e);
    }
}

async function executeAgentBulkNudge() {
    try {
        const res = await fetch(`${BACKEND_BASE_URL}/api/manager/bulk_nudge`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({})
        });
        const data = await res.json();
        if (data && data.success) {
            showToast("Training Nudges Dispatched", data.message, "success");
        }
    } catch (e) {
        console.error("Bulk nudge error:", e);
    }
}

async function quickToggleBgc(email) {
    try {
        const res = await fetch(`${BACKEND_BASE_URL}/api/update_employee_status`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: email, bgc_status: 'Verified' })
        });
        const data = await res.json();
        if (data && data.success) {
            showToast("BGC Verified", `Updated verification for ${email}.`, "success");
            await loadManagerSession(currentManager.email);
        }
    } catch (e) {
        console.error("BGC error:", e);
    }
}

function viewEmployeeJourney(email) {
    activeViewingMode = "employee";
    const sel = document.getElementById('manager-view-as-select');
    if (sel) sel.value = email;
    document.getElementById('manager-override-banner').classList.remove('hidden');
    document.getElementById('override-employee-name').innerText = email;
    loadEmployeeSession(email);
    showToast("Manager Perspective Override", `Inspecting onboarding workflow for ${email}.`, "info");
}

function returnToManagerDashboard() {
    activeViewingMode = "manager";
    const sel = document.getElementById('manager-view-as-select');
    if (sel) sel.value = "manager_dashboard";
    document.getElementById('manager-override-banner').classList.add('hidden');
    loadManagerSession(currentManager.email);
}

function handleManagerViewAsChange(val) {
    if (val === "manager_dashboard") {
        returnToManagerDashboard();
    } else {
        viewEmployeeJourney(val);
    }
}

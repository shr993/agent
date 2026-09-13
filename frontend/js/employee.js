/**
 * OnboardAI - Employee Dashboard, Connected Circular Stepper & Tool Permissions.
 */
async function loadEmployeeSession(email, isSync = false) {
    currentUserRole = activeViewingMode === "employee" && currentManager ? "manager" : "employee";
    try {
        const res = await fetch(`${BACKEND_BASE_URL}/api/user?email=${encodeURIComponent(email)}`);
        const data = await res.json();
        if (data && data.success && data.user) {
            currentEmployee = data.user;
            updateNavigationUI(currentUserRole, email, data.user.name);
            renderEmployeeDashboard(data.user);
            if (isSync) showToast("Profile Synchronized", `Onboarding workflow updated for ${data.user.name}.`, "info");
        }
    } catch (e) {
        console.warn("Employee load notice:", e);
    }
}

function renderEmployeeDashboard(user) {
    document.getElementById('employee-view-container').classList.remove('hidden');
    document.getElementById('manager-view-container').classList.add('hidden');

    const firstName = user.name ? user.name.split(' ')[0] : 'there';
    document.getElementById('hero-name').innerText = firstName;

    // Workflow Milestones Calculation
    let completed = 0;
    const m1Done = (user.profile_created || "").toLowerCase() === "yes";
    if (m1Done) completed++;

    const m2Done = (user.bgc_status || "").toLowerCase() === "verified";
    if (m2Done) completed++;

    const trainings = user.trainings || [];
    const totalTr = trainings.length || 4;
    const completedTr = trainings.filter(t => (t.status || "").toLowerCase() === "completed").length;
    const m3Done = completedTr === totalTr && totalTr > 0;
    if (m3Done) completed++;

    const m4Done = (user.credentials_sent || "").toLowerCase() === "yes";
    if (m4Done) completed++;

    const m5Done = m1Done && m2Done && m3Done && m4Done;
    if (m5Done) completed++;

    const pct = Math.round((completed / 5) * 100);
    document.getElementById('progress-percent').innerText = `${pct}%`;
    document.getElementById('milestones-count').innerText = `${completed} of 5 Completed`;
    document.getElementById('main-progress-bar').style.width = `${pct}%`;

    // Stepper Circular Nodes
    setWorkflowNode(1, m1Done ? 'completed' : 'active', m1Done ? 'Completed' : 'Pending', '✓');
    updateFlowLine('flow-line-1', 'flow-arrow-1', m1Done);

    setWorkflowNode(2, m2Done ? 'completed' : (m1Done ? 'active' : 'locked'), m2Done ? 'Verified' : 'Pending Review', '✓');
    updateFlowLine('flow-line-2', 'flow-arrow-2', m2Done);

    setWorkflowNode(3, m3Done ? 'completed' : (completedTr > 0 ? 'active' : 'locked'), `${completedTr} of ${totalTr} Done`, '📚');
    updateFlowLine('flow-line-3', 'flow-arrow-3', m3Done);

    setWorkflowNode(4, m4Done ? 'completed' : (m2Done && m3Done ? 'active' : 'locked'), m4Done ? 'Active' : 'Pending', '💻');
    updateFlowLine('flow-line-4', 'flow-arrow-4', m4Done);

    setWorkflowNode(5, m5Done ? 'completed' : 'locked', m5Done ? 'Ready! 🎉' : 'Upcoming', '⭐');

    // Tool Permissions
    renderToolAccessList(user.access_requests || []);

    // Trainings Checklist
    renderTrainingsList(trainings, completedTr, totalTr);

    // AI Assistant for Employee
    renderAIChatUI("employee", user);
}

function setWorkflowNode(stepNumber, state, statusText, iconChar) {
    const circle = document.getElementById(`step-circle-${stepNumber}`);
    const badge = document.getElementById(`step-badge-${stepNumber}`);
    const icon = document.getElementById(`step-icon-${stepNumber}`);
    if (!circle || !badge) return;

    if (state === 'completed') {
        circle.className = "w-11 h-11 rounded-full bg-emerald-600 text-white flex items-center justify-center font-bold text-sm shadow-md shadow-emerald-500/30 transition duration-500";
        badge.innerText = statusText;
        badge.className = "text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200";
        if (icon) icon.innerText = "✓";
    } else if (state === 'active') {
        circle.className = "w-11 h-11 rounded-full bg-blue-600 text-white flex items-center justify-center font-bold text-sm ring-4 ring-blue-100 shadow-md transition duration-500 animate-pulse";
        badge.innerText = statusText;
        badge.className = "text-[10px] font-bold px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200";
        if (icon) icon.innerText = iconChar;
    } else {
        circle.className = "w-11 h-11 rounded-full bg-slate-100 text-slate-400 flex items-center justify-center font-bold text-sm border border-slate-200 transition duration-500";
        badge.innerText = statusText;
        badge.className = "text-[10px] font-bold px-2 py-0.5 rounded-full bg-slate-100 text-slate-400 border border-slate-200";
        if (icon) icon.innerText = "🔒";
    }
}

function updateFlowLine(lineId, arrowId, isDone) {
    const line = document.getElementById(lineId);
    const arrow = document.getElementById(arrowId);
    if (line) {
        line.style.width = isDone ? "100%" : "0%";
        line.className = isDone ? "h-full bg-emerald-500 rounded-full transition-all duration-1000" : "h-full bg-slate-300 rounded-full transition-all duration-1000";
    }
    if (arrow) arrow.className = isDone ? "absolute -top-1.5 right-0 text-[10px] text-emerald-600 font-bold" : "absolute -top-1.5 right-0 text-[10px] text-slate-400 font-bold";
}

function renderToolAccessList(reqs) {
    const reqMap = {};
    reqs.forEach(r => reqMap[r.tool_name] = r.status);

    const standardTools = [
        { name: "AWS Dev Sandbox", cat: "Cloud Infrastructure" },
        { name: "GitHub Enterprise", cat: "Version Control" },
        { name: "Corporate VPN Gateway", cat: "Security & Network" },
        { name: "Jira & Confluence Suite", cat: "Collaboration" }
    ];

    const container = document.getElementById('employee-tools-grid');
    if (!container) return;

    container.innerHTML = standardTools.map(t => {
        const status = reqMap[t.name];
        let actionBtn = "";
        if (status === "Approved") {
            actionBtn = `<span class="px-2.5 py-1 text-xs font-bold bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-xl">✓ Active</span>`;
        } else if (status === "Pending") {
            actionBtn = `<span class="px-2.5 py-1 text-xs font-bold bg-amber-50 text-amber-700 border border-amber-200 rounded-xl animate-pulse">⏳ Pending</span>`;
        } else {
            actionBtn = `<button onclick="requestTool('${t.name}', '${t.cat}')" class="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold rounded-xl transition cursor-pointer">Request Access</button>`;
        }

        return `
            <div class="p-3.5 rounded-2xl border border-slate-200 bg-white hover:border-blue-200 shadow-2xs transition flex items-center justify-between gap-3">
                <div class="flex items-center gap-2.5">
                    <div class="w-8 h-8 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center font-bold text-sm">
                        ⚡
                    </div>
                    <div>
                        <div class="text-xs font-bold text-slate-900">${t.name}</div>
                        <div class="text-[10px] text-slate-400">${t.cat}</div>
                    </div>
                </div>
                ${actionBtn}
            </div>
        `;
    }).join('');
}

async function requestTool(toolName, category) {
    try {
        const res = await fetch(`${BACKEND_BASE_URL}/api/request_access`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: currentEmployee.email, tool_name: toolName, tool_category: category })
        });
        const data = await res.json();
        if (data && data.success) {
            showToast("Access Requested", data.message, "success");
            await loadEmployeeSession(currentEmployee.email);
        }
    } catch (e) {
        console.error("Request access error:", e);
    }
}

function renderTrainingsList(trainings, completedCount, totalCount) {
    const grid = document.getElementById('trainings-grid');
    if (!grid) return;
    grid.innerHTML = trainings.map(t => {
        const isDone = (t.status || "").toLowerCase() === "completed";
        return `
            <div class="p-3.5 rounded-2xl border ${isDone ? 'border-emerald-200 bg-emerald-50/20' : 'border-slate-200 bg-white'} shadow-2xs transition flex items-center justify-between gap-3">
                <div class="flex items-center gap-3">
                    <div class="w-8 h-8 rounded-xl bg-slate-100 flex items-center justify-center text-sm">📚</div>
                    <div>
                        <div class="text-xs font-bold text-slate-800">${t.name}</div>
                        <div class="text-[10px] text-slate-400">Compliance Module</div>
                    </div>
                </div>
                <span class="text-[11px] font-bold px-2.5 py-0.5 rounded-full ${isDone ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-slate-100 text-slate-600'}">
                    ${isDone ? '✓ Completed' : 'Pending'}
                </span>
            </div>
        `;
    }).join('');
}

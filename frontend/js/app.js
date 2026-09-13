/**
 * OnboardAI - Global Application State, Authentication & UI Utilities.
 */
const BACKEND_BASE_URL = window.location.origin.includes(":5000") ? window.location.origin : "http://127.0.0.1:5000";

let currentUserRole = "employee"; // "employee" or "manager"
let currentEmployee = null;
let currentManager = null;
let activeViewingMode = "employee"; // When manager inspects employee
let notificationsLog = [];

// DOMContentLoaded
window.addEventListener('DOMContentLoaded', async () => {
    const savedEmail = localStorage.getItem('onboard_user_email');
    const savedRole = localStorage.getItem('onboard_user_role') || "employee";
    const savedName = localStorage.getItem('onboard_user_name') || "";

    if (savedEmail) {
        // Automatically populate underlying dashboard
        if (savedRole === "manager") {
            await loadManagerSession(savedEmail);
        } else {
            await loadEmployeeSession(savedEmail);
        }
    } else {
        // Pre-load default employee view in background
        await loadEmployeeSession("shraddhawarade85@gmail.com");
    }
});

function selectLoginRole(role) {
    currentUserRole = role;
    const empTab = document.getElementById('role-tab-employee');
    const mgrTab = document.getElementById('role-tab-manager');
    const title = document.getElementById('modal-title');
    const desc = document.getElementById('modal-desc');
    const icon = document.getElementById('modal-role-icon');

    if (role === "manager") {
        mgrTab.className = "flex-1 py-2 rounded-xl text-xs font-bold transition bg-white text-indigo-700 shadow-xs flex items-center justify-center gap-1.5 cursor-pointer";
        empTab.className = "flex-1 py-2 rounded-xl text-xs font-bold transition text-slate-600 hover:text-slate-900 flex items-center justify-center gap-1.5 cursor-pointer";
        title.innerText = "Manager Operations Login";
        desc.innerText = "Sign in to access team oversight, sandbox approvals, and onboarding intelligence.";
        icon.innerText = "👔";
        icon.className = "w-12 h-12 bg-indigo-50 text-indigo-600 rounded-2xl flex items-center justify-center mx-auto mb-3 shadow-xs text-xl font-bold";
    } else {
        empTab.className = "flex-1 py-2 rounded-xl text-xs font-bold transition bg-white text-blue-700 shadow-xs flex items-center justify-center gap-1.5 cursor-pointer";
        mgrTab.className = "flex-1 py-2 rounded-xl text-xs font-bold transition text-slate-600 hover:text-slate-900 flex items-center justify-center gap-1.5 cursor-pointer";
        title.innerText = "Employee Portal Login";
        desc.innerText = "Enter your full name and work email to access your personalized Day 1 journey.";
        icon.innerText = "👤";
        icon.className = "w-12 h-12 bg-blue-50 text-blue-600 rounded-2xl flex items-center justify-center mx-auto mb-3 shadow-xs text-xl font-bold";
    }
}

async function handleProfileSubmit() {
    const nameInput = document.getElementById('login-name-input');
    const emailInput = document.getElementById('login-email-input');
    const name = nameInput.value.trim();
    const email = emailInput.value.trim().toLowerCase();

    if (!name || !email) {
        alert("Please provide both Full Name and Email Address.");
        return;
    }

    localStorage.setItem('onboard_user_email', email);
    localStorage.setItem('onboard_user_name', name);
    localStorage.setItem('onboard_user_role', currentUserRole);

    closeProfileModal();

    try {
        await fetch(`${BACKEND_BASE_URL}/api/user/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: name, email: email, role: currentUserRole })
        });
    } catch (e) {
        console.warn("Login sync notice:", e);
    }

    if (currentUserRole === "manager") {
        await loadManagerSession(email);
        showToast("Manager Mode Active", `Signed in as Manager: ${name}.`, "success");
    } else {
        await loadEmployeeSession(email);
        showToast("Employee Journey Active", `Signed in as Employee: ${name}.`, "success");
    }
}

function openProfileModal() {
    document.getElementById('login-overlay').classList.remove('hidden');
    if (mediaRecorder && mediaRecorder.state === "recording") {
        updateRecordingButtonState(true);
        const mins = String(Math.floor(recordingSeconds / 60)).padStart(2, '0');
        const secs = String(recordingSeconds % 60).padStart(2, '0');
        const modalBtnText = document.getElementById('modal-record-btn-text');
        if (modalBtnText) modalBtnText.innerText = `Stop (${mins}:${secs})`;
    }
}

function closeProfileModal() {
    document.getElementById('login-overlay').classList.add('hidden');
}

function updateNavigationUI(role, email, name) {
    const roleBadge = document.getElementById('header-role-badge');
    const portalTitle = document.getElementById('header-portal-title');
    const mgrControls = document.getElementById('manager-perspective-controls');
    const navName = document.getElementById('nav-user-name');
    const navEmail = document.getElementById('nav-user-email');
    const avatar = document.getElementById('user-avatar');

    if (navName) navName.innerText = name || email.split('@')[0];
    if (navEmail) navEmail.innerText = email;
    if (avatar) {
        const initials = (name || email).split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase();
        avatar.innerText = initials || "U";
    }

    if (role === "manager") {
        if (roleBadge) {
            roleBadge.className = "text-[10px] font-extrabold px-2 py-0.5 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200";
            roleBadge.innerText = "👔 Manager Mode";
        }
        if (portalTitle) portalTitle.innerText = "Manager Operations & Approvals Hub";
        if (mgrControls) mgrControls.classList.remove('hidden');
    } else {
        if (roleBadge) {
            roleBadge.className = "text-[10px] font-extrabold px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200";
            roleBadge.innerText = "👤 Employee";
        }
        if (portalTitle) portalTitle.innerText = "Employee Onboarding Journey";
        if (mgrControls && currentUserRole !== "manager") mgrControls.classList.add('hidden');
    }
}

function showToast(title, message, type = "info") {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = "pointer-events-auto bg-white/95 backdrop-blur-md border border-slate-200 shadow-xl rounded-2xl p-3.5 flex items-start gap-3 max-w-sm w-full animate-slide-in transition-all duration-300 ring-1 ring-black/5";
    
    let icon = "⚡";
    let iconBg = "bg-blue-600";
    if (type === "success") { icon = "✓"; iconBg = "bg-emerald-600"; }
    else if (type === "warning") { icon = "⚠️"; iconBg = "bg-amber-600"; }

    toast.innerHTML = `
        <div class="w-7 h-7 rounded-xl ${iconBg} text-white flex items-center justify-center font-bold text-xs shadow-xs shrink-0">
            ${icon}
        </div>
        <div class="flex-1 min-w-0">
            <div class="text-xs font-bold text-slate-900">${title}</div>
            <div class="text-[11px] text-slate-600 mt-0.5 leading-snug">${message}</div>
        </div>
        <button class="text-slate-400 hover:text-slate-700 p-1 text-xs font-bold" onclick="this.parentElement.remove()">✕</button>
    `;
    container.appendChild(toast);
    setTimeout(() => {
        if (toast.parentElement) {
            toast.style.opacity = '0';
            toast.style.transform = 'translateX(100%)';
            setTimeout(() => toast.remove(), 300);
        }
    }, 5000);

    // Save to notifications log
    notificationsLog.unshift({ title, message, time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) });
    updateNotifBell();
}

function updateNotifBell() {
    const badge = document.getElementById('notif-badge');
    const list = document.getElementById('notif-dropdown-list');
    if (badge) {
        badge.innerText = notificationsLog.length;
        badge.style.display = notificationsLog.length > 0 ? "flex" : "none";
    }
    if (list) {
        list.innerHTML = notificationsLog.length === 0 ? '<div class="p-4 text-center text-xs text-slate-400">No notifications</div>' :
            notificationsLog.map(n => `
                <div class="p-3 hover:bg-slate-50 transition flex items-start gap-2.5">
                    <span class="w-2 h-2 rounded-full bg-blue-500 mt-1.5 shrink-0"></span>
                    <div>
                        <div class="text-xs font-bold text-slate-800">${n.title}</div>
                        <div class="text-[11px] text-slate-500 mt-0.5">${n.message}</div>
                    </div>
                </div>
            `).join('');
    }
}

function toggleNotificationDropdown() {
    const drop = document.getElementById('notif-dropdown');
    if (drop) drop.classList.toggle('hidden');
}

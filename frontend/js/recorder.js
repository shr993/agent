/**
 * OnboardAI - In-Browser Screen Recorder Engine
 * Native MediaRecorder + getDisplayMedia implementation with live timer and preview modal.
 */
let mediaRecorder = null;
let recordedChunks = [];
let recordingStream = null;
let recordingTimerInterval = null;
let recordingSeconds = 0;
let recordedVideoBlob = null;

async function toggleScreenRecording() {
    if (mediaRecorder && mediaRecorder.state === "recording") {
        stopScreenRecording();
    } else {
        await startScreenRecording();
    }
}

async function startScreenRecording() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getDisplayMedia) {
        showToast("Screen Recording Error", "Screen recording is not supported on this browser.", "warning");
        return;
    }
    try {
        try {
            recordingStream = await navigator.mediaDevices.getDisplayMedia({
                video: { cursor: "always" },
                audio: true
            });
        } catch (audioErr) {
            recordingStream = await navigator.mediaDevices.getDisplayMedia({
                video: { cursor: "always" },
                audio: false
            });
        }

        recordedChunks = [];
        let mimeType = 'video/webm;codecs=vp9,opus';
        if (!MediaRecorder.isTypeSupported(mimeType)) mimeType = 'video/webm;codecs=vp8,opus';
        if (!MediaRecorder.isTypeSupported(mimeType)) mimeType = 'video/webm';
        if (!MediaRecorder.isTypeSupported(mimeType)) mimeType = '';

        mediaRecorder = mimeType ? new MediaRecorder(recordingStream, { mimeType }) : new MediaRecorder(recordingStream);

        mediaRecorder.ondataavailable = (event) => {
            if (event.data && event.data.size > 0) {
                recordedChunks.push(event.data);
            }
        };

        mediaRecorder.onstop = () => {
            recordedVideoBlob = new Blob(recordedChunks, { type: 'video/webm' });
            showRecordingPreviewModal();
        };

        recordingStream.getVideoTracks()[0].onended = () => {
            if (mediaRecorder && mediaRecorder.state === "recording") {
                stopScreenRecording();
            }
        };

        mediaRecorder.start(1000);
        recordingSeconds = 0;
        updateRecordingButtonState(true);
        startRecordingTimer();
        showToast("Screen Recording Started", "Recording live from login. Click Stop when finished to download.", "info");

    } catch (err) {
        console.warn("Screen recording cancelled:", err);
        updateRecordingButtonState(false);
    }
}

function stopScreenRecording() {
    if (mediaRecorder && mediaRecorder.state === "recording") {
        mediaRecorder.stop();
    }
    if (recordingStream) {
        recordingStream.getTracks().forEach(track => track.stop());
        recordingStream = null;
    }
    stopRecordingTimer();
    updateRecordingButtonState(false);
}

function startRecordingTimer() {
    clearInterval(recordingTimerInterval);
    recordingSeconds = 0;
    const btnText = document.getElementById('record-btn-text');
    const modalBtnText = document.getElementById('modal-record-btn-text');
    const floatTimer = document.getElementById('floating-record-timer');

    recordingTimerInterval = setInterval(() => {
        recordingSeconds++;
        const mins = String(Math.floor(recordingSeconds / 60)).padStart(2, '0');
        const secs = String(recordingSeconds % 60).padStart(2, '0');
        const formatted = `${mins}:${secs}`;
        if (btnText) btnText.innerText = `Stop (${formatted})`;
        if (modalBtnText) modalBtnText.innerText = `Stop (${formatted})`;
        if (floatTimer) floatTimer.innerText = formatted;
    }, 1000);
}

function stopRecordingTimer() {
    clearInterval(recordingTimerInterval);
    const btnText = document.getElementById('record-btn-text');
    const modalBtnText = document.getElementById('modal-record-btn-text');
    if (btnText) btnText.innerText = "Record Screen";
    if (modalBtnText) modalBtnText.innerText = "Start Recording";
}

function updateRecordingButtonState(isRecording) {
    const btn = document.getElementById('screen-record-btn');
    const dot = document.getElementById('record-dot');
    const modalBtn = document.getElementById('modal-screen-record-btn');
    const modalDot = document.getElementById('modal-record-dot');
    const modalIndicator = document.getElementById('modal-record-indicator');
    const floatWidget = document.getElementById('floating-record-bar');

    if (isRecording) {
        if (btn) btn.className = "flex items-center gap-1.5 text-xs font-bold text-white bg-rose-600 hover:bg-rose-700 px-3 py-1.5 rounded-xl shadow-md transition cursor-pointer";
        if (dot) dot.className = "w-2.5 h-2.5 rounded-full bg-white animate-ping";
        if (modalBtn) modalBtn.className = "px-3.5 py-2 bg-slate-900 hover:bg-slate-800 text-white font-bold text-xs rounded-xl shadow-md transition flex items-center gap-1.5 cursor-pointer";
        if (modalDot) modalDot.className = "w-2.5 h-2.5 rounded-full bg-rose-500 animate-ping";
        if (modalIndicator) modalIndicator.classList.remove('hidden');
        if (floatWidget) floatWidget.classList.remove('hidden');
    } else {
        if (btn) btn.className = "flex items-center gap-1.5 text-xs font-bold text-rose-700 bg-rose-50 hover:bg-rose-100 border border-rose-200 px-3 py-1.5 rounded-xl transition cursor-pointer";
        if (dot) dot.className = "w-2.5 h-2.5 rounded-full bg-rose-600";
        if (modalBtn) modalBtn.className = "px-3.5 py-2 bg-rose-600 hover:bg-rose-700 active:scale-95 text-white font-bold text-xs rounded-xl shadow-md transition flex items-center gap-1.5 cursor-pointer";
        if (modalDot) modalDot.className = "w-2.5 h-2.5 rounded-full bg-white";
        if (modalIndicator) modalIndicator.classList.add('hidden');
        if (floatWidget) floatWidget.classList.add('hidden');
    }
}

function showRecordingPreviewModal() {
    if (!recordedVideoBlob) return;
    const modal = document.getElementById('recording-modal');
    const videoEl = document.getElementById('recording-preview-player');
    const metaEl = document.getElementById('recording-meta-info');

    if (modal && videoEl) {
        videoEl.src = URL.createObjectURL(recordedVideoBlob);
        const sizeMB = (recordedVideoBlob.size / (1024 * 1024)).toFixed(2);
        const mins = String(Math.floor(recordingSeconds / 60)).padStart(2, '0');
        const secs = String(recordingSeconds % 60).padStart(2, '0');
        if (metaEl) metaEl.innerText = `Duration: ${mins}:${secs} • Size: ${sizeMB} MB • Format: WebM`;
        modal.classList.remove('hidden');
        showToast("Screen Recording Ready", `Recording (${mins}:${secs}, ${sizeMB}MB) captured. Click Download to save.`, "success");
    }
}

function closeRecordingModal() {
    const modal = document.getElementById('recording-modal');
    const videoEl = document.getElementById('recording-preview-player');
    if (modal) modal.classList.add('hidden');
    if (videoEl) {
        videoEl.pause();
        videoEl.removeAttribute('src');
    }
}

function downloadCurrentRecording() {
    if (!recordedVideoBlob) return;
    const a = document.createElement('a');
    a.style.display = 'none';
    a.href = URL.createObjectURL(recordedVideoBlob);
    const dateStr = new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-');
    a.download = `onboardai-demo-${dateStr}.webm`;
    document.body.appendChild(a);
    a.click();
    setTimeout(() => {
        document.body.removeChild(a);
        URL.revokeObjectURL(a.href);
    }, 2000);
}

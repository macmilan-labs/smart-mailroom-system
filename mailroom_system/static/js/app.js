// ══════════════════════════════════════════════════════════════════════════
//  Smart Mailroom — app.js  (fixed)
//  Sections:
//    1. Utility helpers
//    2. Parcel / OTP actions
//    3. Face Recognition     (webcam → capture → backend)
//    4. Biometric Terminal   (step tracker for dual-factor modals)
//    5. Fingerprint PIN verify
//    6. Demo utilities
//    7. System status panel
//    8. Guided demo tour
//    9. Biometric Enroll / Verify modals
// ══════════════════════════════════════════════════════════════════════════

// ─── 1. UTILITY ───────────────────────────────────────────────────────────

const SmartMonitor = {
    inc: function(type) {
        let count = parseInt(localStorage.getItem('mon_' + type) || '0', 10);
        localStorage.setItem('mon_' + type, count + 1);
        this.update();
    },
    update: function() {
        ['success', 'failed', 'otp', 'face'].forEach(type => {
            const el = document.getElementById('mon-' + type);
            if (el) el.textContent = localStorage.getItem('mon_' + type) || '0';
        });
    }
};
window.incMon = SmartMonitor.inc.bind(SmartMonitor);

document.addEventListener("DOMContentLoaded", () => {
    SmartMonitor.update();
    
    // ── Global Search Filter ──
    const globalSearch = document.getElementById('globalSearch');
    if (globalSearch) {
        globalSearch.addEventListener('input', (e) => {
            const term = e.target.value.toLowerCase();
            document.querySelectorAll('table').forEach(table => {
                table.querySelectorAll('tbody tr').forEach(row => {
                    row.style.display = row.textContent.toLowerCase().includes(term) ? '' : 'none';
                });
            });
        });
    }

    // ── Theme Toggle ──
    const themeToggle = document.getElementById('themeToggle');
    const themeIcon = document.getElementById('themeIcon');
    if (themeToggle) {
        themeToggle.addEventListener('click', () => {
            const isDark = document.documentElement.classList.toggle('dark');
            if (themeIcon) themeIcon.textContent = isDark ? 'dark_mode' : 'light_mode';
            localStorage.setItem('theme', isDark ? 'dark' : 'light');
        });
        if (localStorage.getItem('theme') === 'light') {
            document.documentElement.classList.remove('dark');
            if (themeIcon) themeIcon.textContent = 'light_mode';
        }
    }
});

/**
 * Toast notification
 * type: "success" | "error" | "info"
 */
function showToast(message, type = "info") {
    const colours = { success: "#16a34a", error: "#dc2626", info: "#4f46e5" };
    const toast = document.createElement("div");
    toast.textContent = message;
    Object.assign(toast.style, {
        position: "fixed", bottom: "28px", left: "50%",
        transform: "translateX(-50%)",
        background: colours[type] || colours.info,
        color: "#fff", padding: "16px 32px", borderRadius: "12px",
        fontWeight: "bold", fontSize: "16px",
        boxShadow: "0 10px 25px rgba(0,0,0,0.2)", zIndex: "9999",
        maxWidth: "90vw", textAlign: "center", transition: "opacity 0.4s ease",
    });
    document.body.appendChild(toast);
    setTimeout(() => { toast.style.opacity = "0"; }, 2600);
    setTimeout(() => { toast.remove(); }, 3100);
}

// ─── FAIL-SAFE OVERRIDE PROMPT ────────────────────────────────────────────
function showFailSafePrompt(title, text, onOverride) {
    const div = document.createElement("div");
    div.className = "fixed inset-0 bg-gray-900/60 backdrop-blur-sm flex items-center justify-center p-4 z-[10000]";
    div.innerHTML = `
        <div class="bg-white rounded-2xl p-6 w-full max-w-md shadow-2xl text-center border-t-4 border-red-500">
            <div class="text-4xl mb-3">⚠️</div>
            <h3 class="text-xl font-bold text-gray-900 mb-2">${title}</h3>
            <p class="text-sm text-gray-600 mb-6">${text}</p>
            <div class="flex flex-col gap-3">
                <button id="btn-override-${Date.now()}" class="w-full bg-red-50 hover:bg-red-100 text-red-700 font-bold py-3 text-sm rounded-xl border border-red-200 flex items-center justify-center gap-2">
                    <span>⚡</span> Demo Mode Override
                </button>
                <button onclick="this.closest('.fixed').remove()" class="w-full bg-gray-50 hover:bg-gray-100 text-gray-700 font-bold py-3 text-sm rounded-xl border border-gray-200">
                    Cancel
                </button>
            </div>
        </div>`;
    document.body.appendChild(div);
    div.querySelector('button[id^="btn-override"]').onclick = () => { div.remove(); if (onOverride) onOverride(); };
}

// ─── 2. PARCEL / OTP ACTIONS ──────────────────────────────────────────────

document.addEventListener("DOMContentLoaded", () => {
    // seed button in app.js is a fallback; login.html also has its own
    const seedBtn = document.getElementById("seed-btn");
    if (seedBtn && !seedBtn.dataset.bound) {
        seedBtn.dataset.bound = "1";
        seedBtn.addEventListener("click", async () => {
            try {
                const res  = await fetch("/api/seed", { method: "POST" });
                const data = await res.json();
                showToast(data.msg || "Seed completed", "success");
            } catch (e) {
                showToast("Error seeding DB", "error");
            }
        });
    }
});

async function createParcel(event) {
    event.preventDefault();
    const btn = event.target.querySelector('button[type="submit"]');
    const oldText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = "Processing...";

    const pid   = document.getElementById("parcel_id").value.trim();
    const sname = document.getElementById("student_username").value.trim();
    try {
        const res = await fetch("/api/parcels", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ id: pid, student_username: sname }),
        });
        if (res.ok) {
            showToast("Parcel Created ✅", "success");
            setTimeout(() => window.location.reload(), 1200);
        } else {
            const err = await res.json();
            showToast(err.detail || "Error creating parcel", "error");
            btn.disabled = false;
            btn.innerHTML = oldText;
        }
    } catch (e) {
        showToast("Failed to connect to server.", "error");
        btn.disabled = false;
        btn.innerHTML = oldText;
    }
}

async function markArrived(parcelId, btnElement) {
    if (!confirm(`Mark ${parcelId} as arrived and generate OTP?`)) return;
    
    let oldText = "";
    if (btnElement) {
        oldText = btnElement.innerHTML;
        btnElement.disabled = true;
        btnElement.innerHTML = "Processing...";
    }

    try {
        const res = await fetch(`/api/parcels/${parcelId}/arrive`, { method: "POST" });
        if (res.ok) {
            showToast("Parcel Arrived — OTP Generated ✅", "success");
            setTimeout(() => window.location.reload(), 1200);
        } else {
            const err = await res.json();
            showToast(err.detail || "Error", "error");
            if (btnElement) { btnElement.disabled = false; btnElement.innerHTML = oldText; }
        }
    } catch (e) {
        showToast("Failed to connect to server.", "error");
        if (btnElement) { btnElement.disabled = false; btnElement.innerHTML = oldText; }
    }
}

async function verifyOtp(event) {
    event.preventDefault();
    const btn = event.target.querySelector('button[type="submit"]');
    const oldText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = "Processing...";

    const pid = document.getElementById("verify_parcel_id").value.trim();
    const otp = document.getElementById("verify_otp").value.trim();

    const formData = new URLSearchParams();
    formData.append("parcel_id", pid);
    formData.append("otp", otp);

    try {
        const res = await fetch("/api/verify-otp", {
            method: "POST",
            headers: { "Content-Type": "application/x-www-form-urlencoded" },
            body: formData,
        });
        if (res.ok) {
            showToast("✅ Parcel Collected", "success");
            if (window.incMon) { window.incMon('success'); window.incMon('otp'); }
            setTimeout(() => window.location.reload(), 1200);
        } else {
            if (window.incMon) window.incMon('failed');
            const err = await res.json();
            showToast("❌ " + (err.detail || "OTP Error"), "error");
            btn.disabled = false;
            btn.innerHTML = oldText;
        }
    } catch (e) {
        showToast("Failed to connect to server.", "error");
        btn.disabled = false;
        btn.innerHTML = oldText;
    }
}

// ─── 3. BIOMETRIC TERMINAL (dual-factor step tracker) ─────────────────────
const BiometricTerminal = (() => {
    let _steps = { face: 1, finger: 1 };

    const el = (id) => document.getElementById(id);

    function updateStep(type, step) {
        console.log(`[TERMINAL] ${type} -> step ${step}`);
        _steps[type] = step;
        const statusEl   = el(`${type}StepStatus`);
        const progressEl = el(`${type}StepProgress`);
        const iconEl     = el(`${type}StepIcon`);
        const boxEl      = el(`${type}StepBox`);

        const faceLabels   = ["CAMERA READY", "FACE DETECTED", "MATCHING IDENTITY", "VERIFIED"];
        const fingerLabels = ["AWAITING INPUT", "READING PRINT", "VERIFYING", "VERIFIED"];
        const labels = type === 'face' ? faceLabels : fingerLabels;

        if (statusEl) statusEl.textContent = labels[Math.max(0, step - 1)];
        if (progressEl) {
            const w = step > 0 ? (step / 4) * 100 : 0;
            progressEl.style.transition = "width 1.2s cubic-bezier(0.4, 0, 0.2, 1)";
            progressEl.style.width = `${w}%`;
        }

        const isFail     = (step === -1);
        const isVerified = (step === 4);

        if (isVerified) {
            if (iconEl)  { iconEl.textContent = "check_circle"; iconEl.classList.remove("text-red-500"); iconEl.classList.add("text-emerald-500", "fill-icon"); }
            if (boxEl)   { boxEl.classList.remove('border-red-500/50', 'bg-red-500/5'); boxEl.classList.add('border-emerald-500/50', 'bg-emerald-500/5'); }
        } else if (isFail) {
            _steps[type] = 0;
            if (statusEl)  statusEl.textContent = type === 'face' ? 'FACE NOT RECOGNIZED' : 'VERIFICATION FAILED';
            if (progressEl) progressEl.style.width = '0%';
            if (iconEl)  { iconEl.textContent = "cancel"; iconEl.classList.remove("text-emerald-500", "fill-icon"); iconEl.classList.add("text-red-500"); }
            if (boxEl)   { boxEl.classList.remove('border-emerald-500/50', 'bg-emerald-500/5'); boxEl.classList.add('border-red-500/50', 'bg-red-500/5'); }
        }
        checkAuthReady();
    }

    function checkAuthReady() {
        const btn = el("btnAuthorizeFinal");
        if (btn) {
            const ready = _steps.face === 4 && _steps.finger === 4;
            btn.disabled = !ready;
            if (ready) {
                btn.classList.remove("opacity-50", "cursor-not-allowed");
                btn.classList.add("shadow-[0_0_20px_rgba(16,185,129,0.3)]");
            } else {
                btn.classList.add("opacity-50", "cursor-not-allowed");
                btn.classList.remove("shadow-[0_0_20px_rgba(16,185,129,0.3)]");
            }
        }
    }

    function reset() {
        _steps = { face: 1, finger: 1 };
        ['face', 'finger'].forEach(t => {
            const status   = el(`${t}StepStatus`);
            const progress = el(`${t}StepProgress`);
            const icon     = el(`${t}StepIcon`);
            const box      = el(`${t}StepBox`);
            if (status)   status.textContent = t === 'face' ? "CAMERA READY" : "AWAITING INPUT";
            if (progress) { progress.style.width = "0%"; }
            if (icon)     { icon.textContent = t === 'face' ? "videocam" : "fingerprint"; icon.classList.remove("text-emerald-500", "text-red-500", "fill-icon"); }
            if (box)      box.classList.remove('border-emerald-500/50', 'bg-emerald-500/5', 'border-red-500/50', 'bg-red-500/5');
        });
        const btn = el("btnAuthorizeFinal");
        if (btn) { btn.disabled = true; btn.classList.add("opacity-50", "cursor-not-allowed"); btn.classList.remove("shadow-[0_0_20px_rgba(16,185,129,0.3)]"); }
        const errEl = el("fingerPinError");
        if (errEl) errEl.classList.add('hidden');
    }

    /**
     * Called when user clicks "Finalize Authorization" after both checks pass.
     * On student dashboard: calls /api/verify-biometric to collect parcel.
     * On other contexts: just fires the biometric-finalized event.
     */
    async function finalize() {
        const usernameEl = document.getElementById("faceUsername");
        const username = (usernameEl && usernameEl.value) ? usernameEl.value.trim() : (document.body.dataset.username || "");

        // If we're on the student dashboard, call the full verify-biometric endpoint
        if (username && document.getElementById("faceModal")) {
            const btn = el("btnAuthorizeFinal");
            if (btn) { btn.disabled = true; btn.textContent = "Processing..."; }

            try {
                // We need captured face image and fingerprint pin
                const fingerprintInput = document.getElementById("fingerprintPinInput");
                const fingerprint_id = fingerprintInput ? fingerprintInput.value.trim() : "";
                const face_image = _capturedFaceB64 || "";

                if (!face_image || !fingerprint_id) {
                    showToast("Complete both face and fingerprint verification first.", "error");
                    if (btn) { btn.disabled = false; btn.textContent = "Finalize Authorization"; }
                    return;
                }

                const res = await fetch("/api/verify-biometric", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ username, fingerprint_id, face_image }),
                });
                const data = await res.json();

                if (data.success) {
                    closeFaceModal();
                    if (data.parcel) {
                        showToast(`✅ Identity Verified — Parcel ${data.parcel.id} Released`, "success");
                    } else {
                        showToast("✅ Identity Verified — No parcels awaiting collection", "success");
                    }
                    if (window.incMon) { window.incMon('success'); window.incMon('face'); }
                    setTimeout(() => window.location.reload(), 2000);
                } else {
                    showToast("❌ " + (data.message || "Verification failed"), "error");
                    if (btn) { btn.disabled = false; btn.textContent = "Finalize Authorization"; }
                }
            } catch (e) {
                showToast("Connection error during finalization.", "error");
                if (btn) { btn.disabled = false; btn.textContent = "Finalize Authorization"; }
            }
        } else {
            // Generic finalize (admin enrollment)
            const modal = el("faceModal");
            if (modal) modal.style.display = "none";
            showToast("Access Granted ✅", "success");
            if (typeof stopWebcam === 'function') stopWebcam();
            document.dispatchEvent(new CustomEvent('biometric-finalized'));
        }
    }

    return { updateStep, reset, finalize, checkAuthReady };
})();

// Shared storage for captured face base64 (used by BiometricTerminal.finalize)
let _capturedFaceB64 = null;

// ─── 4. FACE UI ────────────────────────────────────────────────────────────
const FaceUI = (() => {
    let _stream       = null;
    let _capturedBlob = null;
    let _mode         = "register"; // "register" | "verify"
    let _isProcessing = false;

    const el = (id) => document.getElementById(id);

    async function open(mode = "register") {
        _mode = mode;
        _capturedBlob = null;
        _isProcessing = false;
        _capturedFaceB64 = null;

        const modal = el("faceModal");
        if (!modal) return;

        _setStatus("", "");
        _showStep("video");
        modal.style.display = "flex";
        BiometricTerminal.reset();

        await startWebcam();
    }

    function close() {
        stopWebcam();
        const modal = el("faceModal");
        if (modal) modal.style.display = "none";
        _capturedBlob = null;
        _capturedFaceB64 = null;
        _isProcessing = false;
    }

    async function startWebcam() {
        const video = el("faceVideo");
        if (!video) return;
        try {
            _stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "user" } });
            video.srcObject = _stream;
            video.play();
            BiometricTerminal.updateStep('face', 1);
        } catch (err) {
            _setStatus("Camera Error: " + err.message, "error");
        }
    }

    function stopWebcam() {
        if (_stream) { _stream.getTracks().forEach(t => t.stop()); _stream = null; }
        const video = el("faceVideo");
        if (video) video.srcObject = null;
    }

    function captureFace() {
        if (_isProcessing) return;
        const video   = el("faceVideo");
        const canvas  = el("faceCanvas");
        const preview = el("facePreview");

        if (!video || !canvas || !_stream) {
            _setStatus("Camera not ready. Click Retry.", "error");
            return;
        }

        canvas.width  = video.videoWidth  || 640;
        canvas.height = video.videoHeight || 480;
        canvas.getContext("2d").drawImage(video, 0, 0, canvas.width, canvas.height);

        canvas.toBlob((blob) => {
            if (!blob) return;
            _capturedBlob = blob;
            if (preview) { preview.src = URL.createObjectURL(blob); _showStep("preview"); }
            
            BiometricTerminal.updateStep('face', 2);
            _isProcessing = true;

            // Store as base64 for finalize
            const reader = new FileReader();
            reader.onloadend = () => { _capturedFaceB64 = reader.result; };
            reader.readAsDataURL(blob);
            
            setTimeout(() => {
                BiometricTerminal.updateStep('face', 3);
                if (_mode === "verify") {
                    // Verify mode: auto-send to backend
                    setTimeout(() => sendFaceToBackend(), 1000);
                } else {
                    // Register mode: face is captured, advance to "verified" state
                    // so the Finalize button can enable (actual save happens on Finalize click)
                    setTimeout(() => BiometricTerminal.updateStep('face', 4), 1000);
                }
            }, 1000);

            stopWebcam();
        }, "image/jpeg", 0.92);
    }

    async function sendFaceToBackend() {
        if (!_capturedBlob) return;

        // Route: if student verify modal → use session-based verify endpoint
        // If register (admin or student security context) → use update endpoint  
        let endpoint;
        if (_mode === "verify") {
            endpoint = "/api/biometric/face/verify";
        } else {
            // Register mode — update face for currently logged-in user
            endpoint = "/api/biometric/face/update";
        }

        _setBtnLoading(true);

        try {
            const base64 = await _blobToBase64(_capturedBlob);
            const body = JSON.stringify({ face_image: base64 });

            const res  = await fetch(endpoint, {
                method:  "POST",
                headers: { "Content-Type": "application/json" },
                body,
            });
            const data = await res.json();
            _handleFaceResult(data);
        } catch (err) {
            _handleFaceError(err);
        } finally {
            _setBtnLoading(false);
        }
    }

    function _handleFaceResult(data) {
        if (data.success) {
            BiometricTerminal.updateStep('face', 4);
            _setStatus(_mode === "register" ? "✅ Face Enrolled" : "✅ Face Verified", "success");
            if (_mode === "register" && typeof updateSecurityContextUI === 'function') {
                updateSecurityContextUI('face', true);
            }
            if (_mode === "verify" && window.incMon) window.incMon('face');
            // Don't auto-close if there's a Finalize button (dual-factor modal)
            if (!el('btnAuthorizeFinal')) setTimeout(close, 2000);
        } else {
            _handleFaceError(data);
        }
    }

    function _handleFaceError(err) {
        const msg = err.message || (err.detail) || "Face not recognized.";
        BiometricTerminal.updateStep('face', -1);
        _setStatus(msg, "error");
        showToast(msg, "error");
        _isProcessing = false;
    }

    function _setStatus(msg, type) {
        const box = el("faceStatus");
        if (!box) return;
        const colours = { success: "#10b981", error: "#ef4444", info: "#3b82f6", "": "#555" };
        box.textContent = msg;
        box.style.color = colours[type] || colours[""];
        box.style.display = msg ? "block" : "none";
    }

    function _showStep(step) {
        const video   = el("faceVideo");
        const preview = el("facePreview");
        if (video)   video.style.display   = step === "video" ? "block" : "none";
        if (preview) preview.style.display = step === "video" ? "none"  : "block";
    }

    function _setBtnLoading(loading) {
        const btn = el("btnCaptureFace") || el("btnSendFace");
        if (btn) btn.disabled = loading;
    }

    function _blobToBase64(blob) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onloadend = () => resolve(reader.result);
            reader.onerror   = reject;
            reader.readAsDataURL(blob);
        });
    }

    return { open, close, startWebcam, captureFace, sendFaceToBackend };
})();

const openFaceModal    = (mode) => FaceUI.open(mode || "verify");
const closeFaceModal   = ()     => FaceUI.close();
const startWebcam      = ()     => FaceUI.startWebcam();
const captureFace      = ()     => FaceUI.captureFace();
const sendFaceToBackend= ()     => FaceUI.sendFaceToBackend();

// ─── 5. FINGERPRINT PIN VERIFY ────────────────────────────────────────────

async function verifyFingerprintPin() {
    const pinInput = document.getElementById('fingerprintPinInput');
    const errEl    = document.getElementById('fingerPinError');
    const btn      = document.getElementById('btn-verify-fingerprint');

    const pin = pinInput ? pinInput.value.trim() : '';
    if (errEl) errEl.classList.add('hidden');

    if (!pin) {
        if (errEl) { errEl.textContent = 'Please enter your fingerprint PIN.'; errEl.classList.remove('hidden'); }
        return;
    }

    BiometricTerminal.updateStep('finger', 1);
    setTimeout(() => BiometricTerminal.updateStep('finger', 2), 400);
    setTimeout(() => BiometricTerminal.updateStep('finger', 3), 1000);

    if (btn) { btn.disabled = true; btn.textContent = 'Verifying...'; }

    try {
        const res = await fetch('/api/biometric/fingerprint/verify', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({ fingerprint_id: pin }),
        });
        const data = await res.json();

        if (data.success) {
            BiometricTerminal.updateStep('finger', 4);
            showToast('✅ Fingerprint Verified', 'success');
            if (pinInput) pinInput.value = '';
        } else {
            BiometricTerminal.updateStep('finger', -1);
            if (errEl) { errEl.textContent = data.message || 'Verification failed.'; errEl.classList.remove('hidden'); }
            showToast(data.message || 'Fingerprint Verification Failed', 'error');
        }
    } catch (e) {
        BiometricTerminal.updateStep('finger', -1);
        if (errEl) { errEl.textContent = 'Connection error. Please retry.'; errEl.classList.remove('hidden'); }
        showToast('Connection error', 'error');
    } finally {
        if (btn) { btn.disabled = false; btn.textContent = 'Verify Fingerprint'; }
    }
}

// ─── ADMIN: Simulate Fingerprint Scan (Enrollment) ────────────────────────
/**
 * Called from admin enrollment modal "Scan Fingerprint" button.
 * Reads the fingerprint ID input field, simulates a scan, and updates
 * the BiometricTerminal finger steps.
 */
async function simulateFingerprintScan() {
    const fingerprintIdInput = document.getElementById('faceFingerprintId');
    const fingerprintId = fingerprintIdInput ? fingerprintIdInput.value.trim() : '';
    const btn = document.getElementById('btn-sim-fingerprint');

    if (!fingerprintId) {
        showToast('Please enter a Fingerprint ID before scanning.', 'error');
        return;
    }

    if (btn) { btn.disabled = true; btn.textContent = 'Scanning...'; }

    BiometricTerminal.updateStep('finger', 1);
    await new Promise(r => setTimeout(r, 400));
    BiometricTerminal.updateStep('finger', 2);
    await new Promise(r => setTimeout(r, 700));
    BiometricTerminal.updateStep('finger', 3);
    await new Promise(r => setTimeout(r, 700));
    BiometricTerminal.updateStep('finger', 4);

    showToast('✅ Fingerprint Scanned — ready to finalize enrollment', 'success');
    if (btn) { btn.disabled = false; btn.textContent = 'Scan Again'; }
}

// Admin enrollment "Finalize Enrollment" — actually calls /api/register-biometric
async function adminFinalizeEnrollment() {
    const username       = (document.getElementById('faceUsername') || {}).value?.trim() || '';
    const fingerprint_id = (document.getElementById('faceFingerprintId') || {}).value?.trim() || '';
    const face_image     = _capturedFaceB64 || '';
    const btn = document.getElementById('btnAuthorizeFinal');

    if (!username) { showToast('Student username is required.', 'error'); return; }
    if (!fingerprint_id) { showToast('Fingerprint ID is required.', 'error'); return; }
    if (!face_image) { showToast('Please capture a face photo first.', 'error'); return; }
    if (!(document.getElementById('fingerStepStatus')?.textContent?.includes('VERIFIED'))) {
        showToast('Please complete fingerprint scan first.', 'error'); return;
    }

    if (btn) { btn.disabled = true; btn.textContent = 'Registering...'; }

    try {
        const res = await fetch('/api/register-biometric', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({ username, fingerprint_id, face_image }),
        });
        const data = await res.json();
        if (data.success) {
            showToast(`✅ Biometrics Enrolled for ${username}`, 'success');
            closeFaceModal();
        } else {
            showToast('❌ ' + (data.message || 'Registration failed'), 'error');
            if (btn) { btn.disabled = false; btn.textContent = 'Finalize Enrollment'; }
        }
    } catch (e) {
        showToast('Network error during enrollment.', 'error');
        if (btn) { btn.disabled = false; btn.textContent = 'Finalize Enrollment'; }
    }
}

// ─── 6. DEMO UTILITIES ────────────────────────────────────────────────────
let isDemoMode = localStorage.getItem('demoMode') === 'true';

function toggleDemoMode(checked) {
    isDemoMode = checked;
    localStorage.setItem('demoMode', checked);
    applyDemoMode();
    showToast(checked ? "Demo Mode Enabled" : "Demo Mode Disabled", "info");
}

function applyDemoMode() {
    const dot = document.getElementById("demoToggleDot");
    const bg  = document.getElementById("demoToggleBg");
    if (dot && bg) {
        if (isDemoMode) {
            dot.style.transform = "translateX(20px)";
            bg.classList.remove("bg-gray-400"); bg.classList.add("bg-green-500");
        } else {
            dot.style.transform = "translateX(0)";
            bg.classList.add("bg-gray-400"); bg.classList.remove("bg-green-500");
        }
    }

    if (isDemoMode) {
        const u = document.getElementById("username");
        const p = document.getElementById("password");
        if (u && !u.value) u.value = "admin";
        if (p && !p.value) p.value = "admin";

        const tr = document.getElementById("parcel_id");
        if (tr && !tr.value) {
            tr.value = "DEMO-" + Math.floor(Math.random() * 10000);
            const s = document.getElementById("student_username");
            if (s) s.value = "student1";
        }

        if (u && !document.getElementById("demoQuickFill")) {
            const d = document.createElement("div");
            d.id = "demoQuickFill";
            d.className = "flex gap-2 mt-4 demo-only";
            d.innerHTML = `
                <button type="button" onclick="fillLogin && fillLogin('admin','admin','admin')" class="text-[10px] bg-white/5 text-slate-400 border border-white/10 font-bold px-3 py-1.5 rounded-lg hover:bg-white/10 hover:text-white transition-all">Admin Fill</button>
                <button type="button" onclick="fillLogin && fillLogin('student1','password','student')" class="text-[10px] bg-white/5 text-slate-400 border border-white/10 font-bold px-3 py-1.5 rounded-lg hover:bg-white/10 hover:text-white transition-all">Student Fill</button>`;
            const card = u.closest('.dark-card') || u.closest('form');
            if (card) card.appendChild(d);
        }
    }

    document.querySelectorAll(".demo-only").forEach(el => {
        el.style.display = isDemoMode ? "inline-flex" : "none";
    });
}

document.addEventListener("DOMContentLoaded", () => {
    const t = document.getElementById("demoModeToggle");
    if (t) t.checked = isDemoMode;
    applyDemoMode();
});

async function autoGenerateDemoParcel() {
    try {
        const res = await fetch("/api/demo/auto-generate", { method: "POST" });
        if (res.ok) {
            showToast("Demo Parcel Created & OTP Sent ✅", "success");
            setTimeout(() => window.location.reload(), 1200);
        } else {
            showToast("Failed to generate demo parcel", "error");
        }
    } catch (e) {
        showToast("Error", "error");
    }
}

async function instantCollect(parcelId, otp) {
    try {
        const formData = new URLSearchParams();
        formData.append("parcel_id", parcelId);
        formData.append("otp", otp);

        const res = await fetch("/api/verify-otp", {
            method:  "POST",
            headers: { "Content-Type": "application/x-www-form-urlencoded" },
            body:    formData,
        });
        if (res.ok) {
            showToast("✅ Parcel Collected", "success");
            if (window.incMon) { window.incMon('success'); window.incMon('otp'); }
            setTimeout(() => window.location.reload(), 1200);
        } else {
            if (window.incMon) window.incMon('failed');
            showToast("Verification failed", "error");
        }
    } catch (e) {
        showToast("Server error", "error");
    }
}

async function instantFaceVerify() {
    showToast("✅ Face Verified (Demo)", "success");
    if (window.incMon) window.incMon('face');
}

// ─── 7. SYSTEM STATUS PANEL ───────────────────────────────────────────────
async function checkSystemStatus() {
    try {
        const res = await fetch("/api/system/status");
        if (res.ok) {
            const data = await res.json();
            ["backend","database","face","fingerprint","otp"].forEach(k => {
                updateSysStatusUI(k, data[k]);
            });
        } else {
            setAllSysStatusUIError();
        }
    } catch(e) {
        setAllSysStatusUIError();
    }
}

function updateSysStatusUI(key, val) {
    const el = document.getElementById("sys-" + key);
    if (!el) return;
    el.textContent = val ? val.toUpperCase() : "UNKNOWN";
    el.className = (val === "error" || val === "offline") ? "text-red-500 font-bold" : "text-green-500 font-bold";
}

function setAllSysStatusUIError() {
    ["backend","database","face","fingerprint","otp"].forEach(k => {
        const el = document.getElementById("sys-" + k);
        if (el) { el.textContent = "OFFLINE"; el.className = "text-red-500 font-bold"; }
    });
}

document.addEventListener("DOMContentLoaded", () => {
    if (document.getElementById("sys-backend")) {
        checkSystemStatus();
        setInterval(checkSystemStatus, 5000);
    }
});

// ─── 8. GUIDED DEMO TOUR ──────────────────────────────────────────────────
const TOUR_STEPS = {
    1: { title: "Step 1: Admin Login",       desc: "First, authenticate as the system administrator.",                    highlight: "form button[type='submit']" },
    2: { title: "Step 2: Add Parcel",         desc: "Click the Log Delivery button to register a new incoming package.",   highlight: "#btn-add-parcel" },
    3: { title: "Step 3: OTP Sent",           desc: "Marking it as 'Arrived' pings the database and generates an OTP.",   highlight: null },
    4: { title: "Step 4: Student Login",      desc: "Let's switch accounts. We will now log in as the student.",          highlight: "form button[type='submit']" },
    5: { title: "Step 5: Face Verification",  desc: "The student proves identity using biometric face verification.",     highlight: "#btn-verify-face" },
    6: { title: "Step 6: Parcel Collected",   desc: "Once verified, the parcel is released and the loop is complete.",    highlight: null },
};

let currentTourStep = parseInt(localStorage.getItem('tourStep')) || 0;

function startTour() {
    localStorage.setItem('tourStep', '1');
    localStorage.setItem('demoMode', 'true');
    window.location.href = '/logout';
}

function nextTourStep() {
    let s = currentTourStep;
    const btn = document.getElementById('tourNextBtn');
    if (btn) { btn.disabled = true; btn.innerHTML = "Processing..."; }

    if (s === 1) {
        let u = document.getElementById('username');
        if (!u) { window.location.href='/login'; return; }
        u.value = 'admin';
        document.getElementById('password').value = 'admin';
        localStorage.setItem('tourStep', '2');
        document.querySelector('form button[type="submit"]').click();
    } else if (s === 2) {
        const pid = "TOUR-" + Math.floor(Math.random()*1000);
        fetch("/api/parcels", {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ id: pid, student_username: "student1" })
        }).then(() => {
            localStorage.setItem('tourStep', '3');
            localStorage.setItem('tourParcelId', pid);
            window.location.reload();
        }).catch(() => { if (btn) { btn.disabled=false; btn.innerHTML="Next Step ➤"; } });
    } else if (s === 3) {
        const pid = localStorage.getItem('tourParcelId');
        if (pid) {
            fetch(`/api/parcels/${pid}/arrive`, { method: "POST" }).then(() => {
                showToast("OTP Sent ✅", "success");
                localStorage.setItem('tourStep', '4');
                setTimeout(() => { window.location.href = '/logout'; }, 1500);
            });
        } else { endTour(); }
    } else if (s === 4) {
        let u = document.getElementById('username');
        if (!u) { window.location.href='/login'; return; }
        u.value = 'student1';
        document.getElementById('password').value = 'password';
        localStorage.setItem('tourStep', '5');
        document.querySelector('form button[type="submit"]').click();
    } else if (s === 5) {
        const faceBtn = document.getElementById('btn-verify-face') ||
                        document.querySelector("[onclick*='openFaceModal']");
        if (faceBtn) faceBtn.click();
        setTimeout(() => {
            instantFaceVerify();
            localStorage.setItem('tourStep', '6');
            setTimeout(() => { window.location.reload(); }, 1500);
        }, 1200);
    } else if (s === 6) {
        const pid = localStorage.getItem('tourParcelId');
        if (pid) {
            fetch(`/api/demo/force-collect/${pid}`, { method: "POST" }).then(() => {
                showToast("✅ Parcel Collected", "success");
                setTimeout(() => { endTour(); window.location.reload(); }, 1500);
            });
        } else { endTour(); }
    }
}

function endTour() {
    localStorage.removeItem('tourStep');
    localStorage.removeItem('tourParcelId');
    const panel = document.getElementById('guidedTourPanel');
    const sBtn  = document.getElementById('startTourBtn');
    if (panel) panel.style.display = 'none';
    if (sBtn)  sBtn.style.display = 'flex';
    document.querySelectorAll('.tour-highlight').forEach(el =>
        el.classList.remove('tour-highlight', 'ring-4', 'ring-indigo-500', 'ring-offset-2', 'animate-pulse')
    );
}

function renderTourUI() {
    if (currentTourStep === 0) return;

    let panel = document.getElementById('guidedTourPanel');
    if (!panel) {
        panel = document.createElement('div');
        panel.id = 'guidedTourPanel';
        panel.className = "fixed top-8 left-1/2 transform -translate-x-1/2 bg-white rounded-2xl shadow-2xl z-[10000] p-5 text-center border border-indigo-200 w-[340px] md:w-[400px]";
        panel.innerHTML = `
            <div class="mb-3"><span class="bg-indigo-100 text-indigo-800 text-xs font-bold px-3 py-1 rounded-full uppercase tracking-wide">Live Demo Tour</span></div>
            <h4 class="font-bold text-gray-900 text-lg mb-2" id="tourTitle"></h4>
            <p class="text-sm text-gray-600 mb-5 leading-relaxed" id="tourDesc"></p>
            <div class="flex gap-3">
                <button onclick="endTour()" class="flex-1 bg-gray-50 hover:bg-gray-100 text-gray-600 font-bold py-2.5 rounded-xl text-sm border border-gray-200">Exit Tour</button>
                <button id="tourNextBtn" onclick="nextTourStep()" class="flex-1 bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-2.5 rounded-xl text-sm shadow-sm">Next Step ➤</button>
            </div>`;
        document.body.appendChild(panel);
    }

    panel.style.display = 'block';
    const stepData = TOUR_STEPS[currentTourStep];
    if (stepData) {
        document.getElementById('tourTitle').textContent = stepData.title;
        document.getElementById('tourDesc').textContent  = stepData.desc;
        const nb = document.getElementById('tourNextBtn');
        if (nb) nb.innerHTML = currentTourStep === 6 ? "Finish & Collect ✔" : "Next Step ➤";

        document.querySelectorAll('.tour-highlight').forEach(el =>
            el.classList.remove('tour-highlight','ring-4','ring-indigo-500','ring-offset-2','animate-pulse')
        );

        if (stepData.highlight) {
            let target = null;
            if (stepData.highlight.includes(':contains')) {
                const text = stepData.highlight.split("'")[1];
                target = Array.from(document.querySelectorAll('button')).find(b => b.textContent?.includes(text));
            } else {
                target = document.querySelector(stepData.highlight);
            }
            if (target) {
                target.classList.add('tour-highlight','ring-4','ring-indigo-500','ring-offset-2','animate-pulse');
                target.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
        }
    }
}

document.addEventListener("DOMContentLoaded", () => {
    if (!document.getElementById('startTourBtn')) {
        const btn = document.createElement('button');
        btn.id = 'startTourBtn';
        btn.onclick = startTour;
        btn.className = "fixed bottom-10 right-6 bg-gradient-to-r from-indigo-600 to-purple-600 text-white rounded-full p-4 shadow-2xl z-[9000] hover:scale-105 transition-transform flex items-center gap-3 border-2 border-white cursor-pointer";
        btn.innerHTML = `<span class="text-xl">🧭</span> <span class="font-bold text-sm hidden md:inline pr-2">Start Guided Demo</span>`;
        document.body.appendChild(btn);
    }

    if (currentTourStep > 0) {
        const sBtn = document.getElementById('startTourBtn');
        if (sBtn) sBtn.style.display = 'none';
        renderTourUI();
    }
});

// ─── 9. BIOMETRIC ENROLL/VERIFY MODALS (BioModal for admin bioEnrollModal) ─

const BioModal = (() => {
    let _stream      = null;
    let _capturedB64 = null;
    let _activeModal = null; // "enroll" | "verify"

    const $ = (id) => document.getElementById(id);

    function _setStatus(prefix, msg, type) {
        const box = $(`${prefix}Status`);
        if (!box) return;
        const cols = { success: "#16a34a", error: "#dc2626", info: "#4f46e5" };
        box.textContent  = msg;
        box.style.color  = cols[type] || "#555";
        box.style.display = msg ? "block" : "none";
    }

    function _stopStream() {
        if (_stream) { _stream.getTracks().forEach(t => t.stop()); _stream = null; }
    }

    async function _startCamera(videoId, statusPrefix) {
        const video = $(videoId);
        if (!video) return;
        _stopStream();
        try {
            _stream = await navigator.mediaDevices.getUserMedia({
                video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: "user" },
                audio: false,
            });
            video.srcObject = _stream;
            await video.play();
            _setStatus(statusPrefix, "🟢 Camera ready — position your face in the frame", "info");
        } catch (err) {
            _setStatus(statusPrefix, "❌ Camera error: " + err.message, "error");
        }
    }

    function _capture(videoId, previewId, canvasId, captureBtn, retakeBtn, statusPrefix) {
        const video   = $(videoId);
        const canvas  = $(canvasId);
        const preview = $(previewId);
        if (!video || !canvas)  { _setStatus(statusPrefix, "❌ Internal error", "error"); return; }
        if (!_stream)           { _setStatus(statusPrefix, "❌ Camera not active. Click Start Camera.", "error"); return; }

        canvas.width  = video.videoWidth  || 640;
        canvas.height = video.videoHeight || 480;
        canvas.getContext("2d").drawImage(video, 0, 0, canvas.width, canvas.height);

        canvas.toBlob((blob) => {
            if (!blob) { _setStatus(statusPrefix, "❌ Capture failed.", "error"); return; }
            const reader = new FileReader();
            reader.onloadend = () => {
                _capturedB64 = reader.result;
                if (preview) { preview.src = _capturedB64; preview.style.display = "block"; }
                if (video)   video.style.display = "none";
                if ($(captureBtn))  $(captureBtn).style.display  = "none";
                if ($(retakeBtn))   $(retakeBtn).style.display   = "inline-block";
                _setStatus(statusPrefix, "📸 Captured — fill fields then click Submit.", "success");
                _stopStream();
            };
            reader.readAsDataURL(blob);
        }, "image/jpeg", 0.92);
    }

    function _reset(videoId, previewId, captureBtn, retakeBtn, statusPrefix) {
        _capturedB64 = null;
        const video   = $(videoId);
        const preview = $(previewId);
        if (video)   { video.style.display = "block"; video.srcObject = null; }
        if (preview) preview.style.display = "none";
        if ($(captureBtn)) $(captureBtn).style.display = "inline-block";
        if ($(retakeBtn))  $(retakeBtn).style.display  = "none";
        _setStatus(statusPrefix, "", "");
    }

    // ── Enroll (admin #bioEnrollModal) ──────────────────────────────────────
    function openEnroll() {
        _activeModal = "enroll";
        _capturedB64 = null;
        const modal = $("bioEnrollModal");
        if (modal) { modal.style.display = "flex"; }
        _reset("bioEnrollVideo","bioEnrollPreview","bioEnrollCapture","bioEnrollRetake","bioEnroll");
        _startCamera("bioEnrollVideo","bioEnroll");
    }

    function closeEnroll() {
        _stopStream();
        const modal = $("bioEnrollModal");
        if (modal) modal.style.display = "none";
    }

    function captureEnroll() {
        _capture("bioEnrollVideo","bioEnrollPreview","bioEnrollCanvas","bioEnrollCapture","bioEnrollRetake","bioEnroll");
    }

    function retakeEnroll() {
        _reset("bioEnrollVideo","bioEnrollPreview","bioEnrollCapture","bioEnrollRetake","bioEnroll");
        _startCamera("bioEnrollVideo","bioEnroll");
    }

    async function submitEnroll() {
        const username       = ($("bioEnrollUsername") || {}).value?.trim();
        const fingerprint_id = ($("bioEnrollFingerprintId") || {}).value?.trim();

        if (!username)       { _setStatus("bioEnroll","❌ Student username is required.","error"); return; }
        if (!fingerprint_id) { _setStatus("bioEnroll","❌ Fingerprint ID is required.","error"); return; }
        if (!_capturedB64)   { _setStatus("bioEnroll","❌ Please capture a face photo first.","error"); return; }

        _setStatus("bioEnroll","⏳ Registering biometrics…","info");
        const btn = $("bioEnrollSubmit");
        if (btn) { btn.disabled = true; btn.textContent = "Registering…"; }

        try {
            const res  = await fetch("/api/register-biometric", {
                method:  "POST",
                headers: { "Content-Type": "application/json" },
                body:    JSON.stringify({ username, fingerprint_id, face_image: _capturedB64 }),
            });
            const data = await res.json();
            if (data.success) {
                _setStatus("bioEnroll","✅ " + data.message,"success");
                showToast("Biometrics Enrolled ✅","success");
                setTimeout(closeEnroll, 2000);
            } else {
                _setStatus("bioEnroll","❌ " + (data.message || "Registration failed"),"error");
                showToast(data.message || "Registration failed","error");
            }
        } catch (e) {
            _setStatus("bioEnroll","❌ Network error. Check server.","error");
        } finally {
            if (btn) { btn.disabled = false; btn.textContent = "✅ Register Biometrics"; }
        }
    }

    // ── Verify (student #bioVerifyModal) ────────────────────────────────────
    function openVerify() {
        _activeModal = "verify";
        _capturedB64 = null;
        const modal = $("bioVerifyModal");
        if (modal) { modal.style.display = "flex"; }
        _reset("bioVerifyVideo","bioVerifyPreview","bioVerifyCapture","bioVerifyRetake","bioVerify");
        _startCamera("bioVerifyVideo","bioVerify");
    }

    function closeVerify() {
        _stopStream();
        const modal = $("bioVerifyModal");
        if (modal) modal.style.display = "none";
    }

    function captureVerify() {
        _capture("bioVerifyVideo","bioVerifyPreview","bioVerifyCanvas","bioVerifyCapture","bioVerifyRetake","bioVerify");
    }

    function retakeVerify() {
        _reset("bioVerifyVideo","bioVerifyPreview","bioVerifyCapture","bioVerifyRetake","bioVerify");
        _startCamera("bioVerifyVideo","bioVerify");
    }

    async function submitVerify() {
        const username       = document.body.dataset.username || "";
        const fingerprint_id = ($("bioVerifyFingerprintId") || {}).value?.trim();

        if (!username)       { _setStatus("bioVerify","❌ Not logged in.","error"); return; }
        if (!fingerprint_id) { _setStatus("bioVerify","❌ Fingerprint ID is required.","error"); return; }
        if (!_capturedB64)   { _setStatus("bioVerify","❌ Please capture a face photo first.","error"); return; }

        _setStatus("bioVerify","⏳ Verifying identity…","info");
        const btn = $("bioVerifySubmit");
        if (btn) { btn.disabled = true; btn.textContent = "Verifying…"; }

        try {
            const res  = await fetch("/api/verify-biometric", {
                method:  "POST",
                headers: { "Content-Type": "application/json" },
                body:    JSON.stringify({ username, fingerprint_id, face_image: _capturedB64 }),
            });
            const data = await res.json();
            if (data.success) {
                _setStatus("bioVerify","✅ Identity verified!","success");
                showToast("✅ Identity Verified","success");
                if (window.incMon) { window.incMon('success'); window.incMon('face'); }
                setTimeout(closeVerify, 2000);
            } else {
                _setStatus("bioVerify","❌ " + (data.message || "Verification failed"),"error");
                showToast("❌ " + (data.message || "Mismatch"),"error");
                if (window.incMon) window.incMon('failed');
            }
        } catch (e) {
            _setStatus("bioVerify","❌ Network error. Check server.","error");
        } finally {
            if (btn) { btn.disabled = false; btn.textContent = "✅ Verify Identity"; }
        }
    }

    return {
        openEnroll, closeEnroll, captureEnroll, retakeEnroll, submitEnroll,
        openVerify, closeVerify, captureVerify, retakeVerify, submitVerify,
    };
})();

// Global shims for onclick="" attributes
const openBioEnrollModal  = () => BioModal.openEnroll();
const closeBioEnrollModal = () => BioModal.closeEnroll();
const captureBioEnroll    = () => BioModal.captureEnroll();
const retakeBioEnroll     = () => BioModal.retakeEnroll();
const submitBioEnroll     = () => BioModal.submitEnroll();

const openBioVerifyModal  = () => BioModal.openVerify();
const closeBioVerifyModal = () => BioModal.closeVerify();
const captureBioVerify    = () => BioModal.captureVerify();
const retakeBioVerify     = () => BioModal.retakeVerify();
const submitBioVerify     = () => BioModal.submitVerify();

/**
 * Student Security Context — manage biometrics
 * Face: opens the faceModal in register mode (FaceUI)
 * Finger: shows a PIN entry prompt to set/update fingerprint ID
 */
window.manageBio = async function(type) {
    if (type === 'face') {
        FaceUI.open('register');
    } else if (type === 'finger') {
        showFingerprintSetupPrompt();
    }
};

function showFingerprintSetupPrompt() {
    // Remove existing prompt if any
    const existing = document.getElementById('fpSetupPrompt');
    if (existing) existing.remove();

    const div = document.createElement('div');
    div.id = 'fpSetupPrompt';
    div.className = "fixed inset-0 z-[200] flex items-center justify-center bg-black/70 backdrop-blur-sm p-4";
    div.innerHTML = `
        <div class="bg-[#0d0d0e] border border-white/10 rounded-[2rem] p-10 w-full max-w-sm shadow-2xl text-center">
            <div class="w-16 h-16 rounded-2xl bg-secondary/10 border border-secondary/20 flex items-center justify-center mx-auto mb-6">
                <span class="material-symbols-outlined text-secondary text-3xl">fingerprint</span>
            </div>
            <h3 class="text-white font-black text-lg uppercase tracking-widest mb-2">Set Fingerprint PIN</h3>
            <p class="text-xs text-zinc-500 font-bold uppercase tracking-widest mb-8">Enter a PIN phrase to use as your fingerprint identifier</p>
            <input id="fpSetupInput" type="password" placeholder="Enter new PIN phrase"
                class="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white placeholder-zinc-600 focus:outline-none focus:border-secondary/50 mb-4" autocomplete="off" />
            <div class="flex gap-3">
                <button onclick="document.getElementById('fpSetupPrompt').remove()"
                    class="flex-1 py-3 border border-white/10 rounded-xl bg-white/5 text-white text-xs font-bold uppercase tracking-widest hover:bg-white/10 transition-all">Cancel</button>
                <button onclick="submitFingerprintSetup()"
                    class="flex-1 py-3 bg-secondary text-[#002113] rounded-xl text-xs font-black uppercase tracking-widest hover:brightness-110 transition-all">Save</button>
            </div>
            <p id="fpSetupError" class="text-xs text-red-400 font-bold mt-4 hidden"></p>
        </div>`;
    document.body.appendChild(div);
    setTimeout(() => document.getElementById('fpSetupInput')?.focus(), 100);
}

async function submitFingerprintSetup() {
    const input    = document.getElementById('fpSetupInput');
    const errorEl  = document.getElementById('fpSetupError');
    const fingerprint_id = input ? input.value.trim() : '';

    if (!fingerprint_id) {
        if (errorEl) { errorEl.textContent = 'PIN phrase cannot be empty.'; errorEl.classList.remove('hidden'); }
        return;
    }

    try {
        const res = await fetch('/api/biometric/fingerprint/update', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ fingerprint_id }),
        });
        const data = await res.json();
        if (data.success) {
            document.getElementById('fpSetupPrompt')?.remove();
            showToast('✅ Fingerprint PIN Saved', 'success');
            updateSecurityContextUI('finger', true);
        } else {
            if (errorEl) { errorEl.textContent = data.message || 'Save failed.'; errorEl.classList.remove('hidden'); }
        }
    } catch (e) {
        if (errorEl) { errorEl.textContent = 'Connection error.'; errorEl.classList.remove('hidden'); }
    }
}

function updateSecurityContextUI(type, enrolled) {
    // 1. Context tiles
    const tile   = document.getElementById(type + 'Tile');
    const status = document.getElementById(type + 'TileStatus');
    if (tile && status) {
        status.textContent = enrolled ? "Enrolled" : "Not Enrolled";
        const color = enrolled ? 'emerald-500' : 'amber-500';
        status.className = `text-[10px] text-${color} font-black uppercase tracking-widest mt-0.5 truncate`;
        tile.classList.remove('border-emerald-500/10','hover:border-emerald-500/30','border-amber-500/10','hover:border-amber-500/30');
        tile.classList.add(`border-${color}/10`,`hover:border-${color}/30`);
        const iconBox = tile.querySelector('.shrink-0');
        if (iconBox) {
            iconBox.classList.remove('bg-emerald-500/10','border-emerald-500/10','bg-amber-500/10','border-amber-500/10');
            iconBox.classList.add(`bg-${color}/10`,`border-${color}/10`);
            const icon = iconBox.querySelector('.material-symbols-outlined');
            if (icon) { icon.classList.remove('text-emerald-500','text-amber-500'); icon.classList.add(`text-${color}`); }
        }
    }

    // 2. Hero card
    const cardStatus = document.getElementById(`card${type.charAt(0).toUpperCase()+type.slice(1)}Status`);
    if (cardStatus) {
        cardStatus.textContent = enrolled ? "Enrolled" : "Not Enrolled";
        cardStatus.className = `text-[10px] font-black ${enrolled ? 'text-emerald-500' : 'text-zinc-600'} uppercase tracking-widest`;
    }

    // 3. Overall security status
    const faceEnrolled   = document.getElementById('cardFaceStatus')?.textContent.trim()   === 'Enrolled';
    const fingerEnrolled = document.getElementById('cardFingerStatus')?.textContent.trim() === 'Enrolled';
    const fullyEnrolled  = faceEnrolled && fingerEnrolled;

    const cardContainer = document.getElementById('securityCardContainer');
    const statusIcon    = document.getElementById('securityStatusIcon');
    const mainIcon      = document.getElementById('mainStatusIcon');
    const glowEffect    = document.getElementById('securityGlow');

    if (fullyEnrolled) {
        cardContainer?.classList.replace('border-amber-500/20','border-emerald-500/20');
        statusIcon?.classList.remove('bg-amber-500/10','text-amber-500');
        statusIcon?.classList.add('bg-emerald-500/10','text-emerald-500');
        if (mainIcon)   mainIcon.textContent = 'verified';
        if (glowEffect) { glowEffect.classList.replace('bg-amber-500/10','bg-emerald-500/10'); }
    } else {
        cardContainer?.classList.replace('border-emerald-500/20','border-amber-500/20');
        statusIcon?.classList.remove('bg-emerald-500/10','text-emerald-500');
        statusIcon?.classList.add('bg-amber-500/10','text-amber-500');
        if (mainIcon)   mainIcon.textContent = 'lock_open';
        if (glowEffect) { glowEffect.classList.replace('bg-emerald-500/10','bg-amber-500/10'); }
    }
}

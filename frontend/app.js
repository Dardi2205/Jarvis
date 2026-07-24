const activateBtn = document.getElementById("activateBtn");
const statusDot = document.getElementById("statusDot");
const statusText = document.getElementById("statusText");
const voiceOverlay = document.getElementById("voiceOverlay");
const voiceText = document.getElementById("voiceText");
const systemTime = document.getElementById("systemTime");

let history = [];
let isSpeaking = false;
let mediaRecorder = null;
let audioChunks = [];
let micStream = null;
let recording = false;

function updateTime() {
    const n = new Date();
    systemTime.textContent = String(n.getHours()).padStart(2, "0") + ":" +
        String(n.getMinutes()).padStart(2, "0") + ":" +
        String(n.getSeconds()).padStart(2, "0");
}
updateTime();
setInterval(updateTime, 1000);

async function checkHealth() {
    try {
        const r = await fetch("/api/health");
        const d = await r.json();
        const ok = "ok" === d.status;
        statusDot.classList.toggle("off", !ok);
        statusText.textContent = ok ? "ONLINE" : "OFFLINE";
    } catch {
        statusText.textContent = "OFFLINE";
        statusDot.classList.add("off");
    }
}
checkHealth();
setInterval(checkHealth, 15000);

function showOverlay(t) {
    voiceText.textContent = t;
    voiceOverlay.classList.add("on");
}

function hideOverlay() {
    voiceOverlay.classList.remove("on");
}

async function toggleMic() {
    if (recording) {
        stopRecording();
        return;
    }

    if (isSpeaking) {
        window.speechSynthesis.cancel();
        isSpeaking = false;
    }

    try {
        micStream = await navigator.mediaDevices.getUserMedia({ audio: true });
        audioChunks = [];

        let mimeType = "";
        for (const t of ["audio/webm;codecs=opus", "audio/webm", "audio/mp4"]) {
            if (MediaRecorder.isTypeSupported(t)) {
                mimeType = t;
                break;
            }
        }

        mediaRecorder = new MediaRecorder(micStream, mimeType ? { mimeType } : {});

        mediaRecorder.ondataavailable = (e) => {
            if (e.data && e.data.size > 0) {
                audioChunks.push(e.data);
            }
        };

        mediaRecorder.onstop = async () => {
            cleanupMic();
            if (audioChunks.length === 0) {
                hideOverlay();
                statusText.textContent = "NO AUDIO";
                return;
            }
            await processAudio(new Blob(audioChunks, { type: mediaRecorder.mimeType || "audio/webm" }));
        };

        mediaRecorder.onerror = () => {
            cleanupMic();
            hideOverlay();
            statusText.textContent = "ERROR";
        };

        mediaRecorder.start(200);
        recording = true;
        activateBtn.classList.add("on");
        activateBtn.textContent = "PO DËGJOJ...";
        showOverlay("PO DËGJOJ...");
        statusText.textContent = "PO DËGJOJ...";

        setTimeout(() => {
            if (recording && mediaRecorder && mediaRecorder.state === "recording") {
                mediaRecorder.stop();
            }
        }, 10000);

    } catch (e) {
        console.error("Mic error:", e);
        statusText.textContent = "MIKROFON I REFUZUAR";
        hideOverlay();
    }
}

function stopRecording() {
    if (mediaRecorder && mediaRecorder.state === "recording") {
        mediaRecorder.stop();
    } else {
        cleanupMic();
        hideOverlay();
    }
}

function cleanupMic() {
    recording = false;
    if (micStream) {
        micStream.getTracks().forEach((t) => t.stop());
        micStream = null;
    }
    activateBtn.classList.remove("on");
    activateBtn.textContent = "AKTIVIZO JARVIS";
}

async function processAudio(e) {
    showOverlay("PO PERKTHEJ...");
    statusText.textContent = "PO PERKTHEJ...";
    const formData = new FormData();
    formData.append("audio", e, "recording.webm");

    try {
        const r = await fetch("/api/speech-to-text", { method: "POST", body: formData });
        const d = await r.json();
        hideOverlay();
        if (d.text && d.text.trim()) {
            await sendMessage(d.text.trim());
        } else {
            statusText.textContent = "NUK DËGJOVA";
            await speak("Nuk degjova asgje. Provo perseri.");
        }
    } catch (err) {
        console.error("STT error:", err);
        hideOverlay();
        statusText.textContent = "GABIM";
    }
}

async function speak(text) {
    if (!text) return;
    isSpeaking = true;
    statusText.textContent = "PO FLAS...";

    try {
        const r = await fetch("/api/text-to-speech", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text })
        });
        const d = await r.json();

        if (d.audio && d.audio.length > 0) {
            const bytes = new Uint8Array(d.audio);
            const blob = new Blob([bytes], { type: "audio/mpeg" });
            const url = URL.createObjectURL(blob);
            const audio = new Audio(url);
            audio.onend = () => {
                isSpeaking = false;
                URL.revokeObjectURL(url);
                statusText.textContent = "ONLINE";
            };
            audio.onerror = () => {
                isSpeaking = false;
                URL.revokeObjectURL(url);
                fallbackSpeak(text);
            };
            await audio.play();
        } else {
            fallbackSpeak(text);
        }
    } catch {
        fallbackSpeak(text);
    }
}

function fallbackSpeak(text) {
    if (!("speechSynthesis" in window)) {
        isSpeaking = false;
        statusText.textContent = "ONLINE";
        return;
    }
    window.speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text.replace(/[*_`#]/g, ""));
    u.lang = "sq-AL";
    u.onend = () => {
        isSpeaking = false;
        statusText.textContent = "ONLINE";
    };
    window.speechSynthesis.speak(u);
}

async function sendMessage(text) {
    if (!text.trim()) return;
    history.push({ role: "user", content: text });
    statusText.textContent = "PO MENDOJ...";
    showOverlay("PO MENDOJ...");

    try {
        const r = await fetch("/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: text, history: history.slice(-20) })
        });
        const d = await r.json();
        hideOverlay();
        const reply = d.reply || "Gabim.";
        history.push({ role: "assistant", content: reply });
        await speak(reply);
    } catch {
        hideOverlay();
        statusText.textContent = "GABIM";
        await speak("Gabim lidhjeje.");
    }
}

activateBtn.addEventListener("click", toggleMic);

voiceOverlay.addEventListener("click", (e) => {
    if (e.target.id === "overlayClose" && recording) {
        stopRecording();
    }
});

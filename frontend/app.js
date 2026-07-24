const chatArea = document.getElementById("chatArea");
const userInput = document.getElementById("userInput");
const sendBtn = document.getElementById("sendBtn");
const statusDot = document.getElementById("statusDot");
const statusText = document.getElementById("statusText");
const voiceOverlay = document.getElementById("voiceOverlay");
const voiceText = document.getElementById("voiceText");
const systemTime = document.getElementById("systemTime");
const wakeBtn = document.getElementById("wakeBtn");
const chatPanel = document.getElementById("chatPanel");
const chatToggle = document.getElementById("chatToggle");

let history = [];
let isSpeaking = false;
let mediaRecorder = null;
let audioChunks = [];
let micStream = null;
let recording = false;

function updateTime() {
    const now = new Date();
    systemTime.textContent =
        String(now.getHours()).padStart(2,'0') + ":" +
        String(now.getMinutes()).padStart(2,'0') + ":" +
        String(now.getSeconds()).padStart(2,'0');
}
updateTime();
setInterval(updateTime, 1000);

async function checkHealth() {
    try {
        const r = await fetch("/api/health");
        const d = await r.json();
        const online = d.status === "ok";
        statusDot.classList.toggle("off", !online);
        statusText.textContent = online ? "ONLINE" : "OFFLINE";
    } catch {
        statusText.textContent = "OFFLINE";
        statusDot.classList.add("off");
    }
}
checkHealth();
setInterval(checkHealth, 15000);

chatToggle.addEventListener("click", () => chatPanel.classList.toggle("hide"));

function showOverlay(txt) { voiceText.textContent = txt; voiceOverlay.classList.add("on"); }
function hideOverlay() { voiceOverlay.classList.remove("on"); }

async function toggleMic() {
    if (recording) { stopRecording(); return; }
    if (isSpeaking) { window.speechSynthesis.cancel(); isSpeaking = false; }

    try {
        micStream = await navigator.mediaDevices.getUserMedia({ audio: true });
        audioChunks = [];
        let mime = "";
        for (const t of ["audio/webm;codecs=opus", "audio/webm", "audio/mp4"]) {
            if (MediaRecorder.isTypeSupported(t)) { mime = t; break; }
        }
        mediaRecorder = new MediaRecorder(micStream, mime ? { mimeType: mime } : {});
        mediaRecorder.ondataavailable = (e) => { if (e.data && e.data.size > 0) audioChunks.push(e.data); };
        mediaRecorder.onstop = async () => {
            cleanupMic();
            if (audioChunks.length === 0) { hideOverlay(); statusText.textContent = "NO AUDIO"; return; }
            const blob = new Blob(audioChunks, { type: mediaRecorder.mimeType || "audio/webm" });
            await processAudio(blob);
        };
        mediaRecorder.onerror = () => { cleanupMic(); hideOverlay(); statusText.textContent = "ERROR"; };
        mediaRecorder.start(200);
        recording = true;
        wakeBtn.classList.add("on");
        showOverlay("PO DËGJOJ...");
        statusText.textContent = "PO DËGJOJ...";
        setTimeout(() => { if (recording && mediaRecorder && mediaRecorder.state === "recording") mediaRecorder.stop(); }, 10000);
    } catch (err) {
        console.error("Mic error:", err);
        statusText.textContent = "MIKROFON I REFUZUAR";
        hideOverlay();
    }
}

function stopRecording() {
    if (mediaRecorder && mediaRecorder.state === "recording") mediaRecorder.stop();
    else { cleanupMic(); hideOverlay(); }
}

function cleanupMic() {
    recording = false;
    if (micStream) { micStream.getTracks().forEach(t => t.stop()); micStream = null; }
    wakeBtn.classList.remove("on");
}

async function processAudio(blob) {
    showOverlay("PO PERKTHEJ...");
    statusText.textContent = "PO PERKTHEJ...";
    const fd = new FormData();
    fd.append("audio", blob, "recording.webm");
    try {
        const r = await fetch("/api/speech-to-text", { method: "POST", body: fd });
        const d = await r.json();
        hideOverlay();
        if (d.text && d.text.trim()) sendMessage(d.text.trim());
        else { statusText.textContent = "NUK DËGJOVA"; addMessage("Nuk degjova asgje. Provo perseri.", "jarvis"); }
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
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text }),
        });
        const d = await r.json();
        if (d.audio && d.audio.length > 0) {
            const bytes = new Uint8Array(d.audio);
            const blob = new Blob([bytes], { type: "audio/mpeg" });
            const url = URL.createObjectURL(blob);
            const audio = new Audio(url);
            audio.onended = () => { isSpeaking = false; URL.revokeObjectURL(url); statusText.textContent = "ONLINE"; };
            audio.onerror = () => { isSpeaking = false; URL.revokeObjectURL(url); fallbackSpeak(text); };
            await audio.play();
        } else fallbackSpeak(text);
    } catch { fallbackSpeak(text); }
}

function fallbackSpeak(text) {
    if (!("speechSynthesis" in window)) { isSpeaking = false; statusText.textContent = "ONLINE"; return; }
    window.speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text.replace(/[*_`#]/g, ""));
    u.lang = "sq-AL";
    u.onend = () => { isSpeaking = false; statusText.textContent = "ONLINE"; };
    window.speechSynthesis.speak(u);
}

function addMessage(text, sender) {
    const msg = document.createElement("div");
    msg.className = "msg " + sender;
    const av = document.createElement("div");
    av.className = "av";
    av.textContent = sender === "jarvis" ? "J" : "U";
    const bub = document.createElement("div");
    bub.className = "bub";
    bub.textContent = text;
    msg.appendChild(av);
    msg.appendChild(bub);
    chatArea.appendChild(msg);
    chatArea.scrollTop = chatArea.scrollHeight;
}

function addTypingIndicator() {
    const msg = document.createElement("div");
    msg.className = "msg jarvis"; msg.id = "typing";
    const av = document.createElement("div");
    av.className = "av"; av.textContent = "J";
    const ind = document.createElement("div");
    ind.className = "bub typing";
    ind.innerHTML = "<span></span><span></span><span></span>";
    msg.appendChild(av); msg.appendChild(ind);
    chatArea.appendChild(msg);
    chatArea.scrollTop = chatArea.scrollHeight;
}

function removeTypingIndicator() { document.getElementById("typing")?.remove(); }

async function sendMessage(text) {
    if (!text.trim()) return;
    const wakePatterns = /^(hej bylbyl|hej bilbyl|hej makrella|oj makrella|hej bir im)/i;
    if (wakePatterns.test(text.trim())) {
        addMessage(text, "user");
        addMessage("Po dëgjoj! Flit tash...", "jarvis");
        if (!recording) toggleMic();
        return;
    }
    addMessage(text, "user");
    history.push({ role: "user", content: text });
    userInput.value = "";
    addTypingIndicator();
    statusText.textContent = "PO MENDOJ...";
    try {
        const r = await fetch("/api/chat", {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: text, history: history.slice(-20) }),
        });
        const d = await r.json();
        removeTypingIndicator();
        const reply = d.reply || "Gabim.";
        addMessage(reply, "jarvis");
        history.push({ role: "assistant", content: reply });
        await speak(reply);
    } catch {
        removeTypingIndicator();
        addMessage("Gabim lidhjeje.", "jarvis");
        statusText.textContent = "GABIM";
    }
}

wakeBtn.addEventListener("click", toggleMic);
sendBtn.addEventListener("click", () => sendMessage(userInput.value));
userInput.addEventListener("keydown", (e) => { if (e.key === "Enter") sendMessage(userInput.value); });
voiceOverlay.addEventListener("click", (e) => { if (e.target.id === "overlayClose" || e.target === voiceOverlay) { if (recording) stopRecording(); } });

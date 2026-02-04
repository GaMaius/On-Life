
const updateInterval = 500; // 0.5s

function init() {
    setInterval(updateStatus, updateInterval);

    // Enter key for chat
    document.getElementById('chat-input').addEventListener('keypress', function (e) {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });
}

async function updateStatus() {
    try {
        const response = await fetch('/api/status');
        const data = await response.json();

        // 1. Update Profile & Stats
        document.getElementById('hp-bar').style.width = (data.hp / data.max_hp * 100) + '%';
        if (document.getElementById('hp-text')) document.getElementById('hp-text').innerText = Math.floor(data.hp) + ' / ' + data.max_hp;
        document.getElementById('xp-bar').style.width = data.level_progress + '%';
        if (document.getElementById('xp-text')) document.getElementById('xp-text').innerText = Math.floor(data.xp) + ' / ' + data.next_level_xp;
        document.getElementById('level-text').innerText = 'Lv.' + data.level;

        let title = "알 🐣";
        if (data.level >= 1) title = "주니어 병아리 🐥";
        if (data.level >= 5) title = "시니어 병아리 🔥";
        if (data.level >= 10) title = "전설의 개발자 👑";
        document.getElementById('user-title').innerText = title;

        // Character Expression (Main Display)
        const mainChar = document.getElementById('main-char-display');
        let emoji = "🐣";

        if (data.level >= 2) {
            if (data.is_smiling) {
                emoji = "😊";
            } else if (data.is_drowsy) {
                emoji = "😴";
            } else if (data.is_eye_closed) { // Blink
                emoji = "😌";
            } else if (data.is_bad_posture) {
                emoji = "🐢";
            }
            if (document.getElementById('char-emoji')) document.getElementById('char-emoji').innerText = emoji;
        }


        // 2. Posture Status & Damage
        const dot = document.getElementById('posture-dot');
        const text = document.getElementById('posture-text');
        const overlay = document.getElementById('damage-overlay');

        if (data.is_bad_posture) {
            dot.classList.add('bad');
            text.innerText = "거북목 경고! 자세를 고치세요";
            text.style.color = "var(--danger)";
        } else {
            dot.classList.remove('bad');
            text.innerText = "바른 자세 유지중";
            text.style.color = "var(--success)";
        }

        // Damage Overlay Sync
        if (data.is_taking_damage) {
            overlay.classList.add('show');
            overlay.innerText = "⚠️ HP 감소중!";
        } else {
            overlay.classList.remove('show');
        }

        // 3. Render Quests
        renderRequests(data.active_quests, data.available_quests);

    } catch (e) {
        console.error("Status update failed", e);
    }
}

function renderRequests(active, available) {
    const activeContainer = document.getElementById('active-quest-container');
    const availableContainer = document.getElementById('available-quest-list');

    // Render Active
    if (active.length > 0) {
        activeContainer.innerHTML = active.map((q, idx) => `
            <div class="quest-card" onclick='showQuestDetails(${JSON.stringify(q)})' style="cursor:pointer;">
                <div class="quest-header">
                    <span class="quest-title">${q.name}</span>
                    <span class="quest-xp">+${q.reward_xp} XP</span>
                </div>
                <div class="quest-desc">${q.description}</div>
                <div class="quest-progress-wrap">
                    <div class="quest-progress-bar" style="width: ${(q.progress / q.target_duration * 100)}%"></div>
                </div>
            </div>
        `).join('');
    } else {
        activeContainer.innerHTML = '<div class="empty-state">진행중인 퀘스트 없음</div>';
    }

    // Render Available
    if (available.length > 0) {
        availableContainer.innerHTML = available.map((q, idx) => `
            <div class="quest-card">
                 <div class="quest-header" onclick='showQuestDetails(${JSON.stringify(q)})' style="cursor:pointer;">
                    <span class="quest-title">${q.name}</span>
                    <span class="quest-xp">+${q.reward_xp} XP</span>
                </div>
                <div class="quest-desc">${q.description}</div>
                <button class="neumorphic-btn" style="width:100%; justify-content:center; margin-top:10px; font-size:0.9rem;" onclick="acceptQuest(${idx})">
                    수락하기
                </button>
            </div>
        `).join('');
    } else {
        availableContainer.innerHTML = '<div class="empty-state" style="font-size:0.9rem; color:#aaa;">선택 가능한 퀘스트가 없습니다.</div>';
    }
}

function showQuestDetails(quest) {
    const detailsDiv = document.getElementById('quest-details');
    detailsDiv.style.display = 'block';

    document.getElementById('q-condition').innerText = quest.clear_condition;

    // Format duration
    const progress = Math.floor(quest.progress || 0);
    const target = quest.target_duration;
    document.getElementById('q-progress').innerText = `${progress}s / ${target}s (${Math.floor(progress / target * 100)}%)`;

    showModal(quest.name, quest.description, true);
}

async function acceptQuest(index) {
    const res = await fetch('/api/quest/accept', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ index: index })
    });
    const data = await res.json();
    if (data.success) {
        showModal("퀘스트 수락", "퀘스트가 시작되었습니다!");
        updateStatus(); // Immediate refresh
    }
}

async function sendMessage() {
    const input = document.getElementById('chat-input');
    const text = input.value;
    if (!text) return;

    // Add User Message
    addMessage("user", text);
    input.value = "";

    // API Call
    const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text })
    });
    const data = await res.json();

    if (data.response) {
        // 1. Show Thought (if any)
        if (data.thought) {
            addThought(data.thought);
        }

        addMessage("assistant", data.response);
        speak(data.response); // Trigger TTS

        // Handle Task/Schedule
        if (data.task) {
            console.log("New Task:", data.task);
            addSchedule(data.task);
        }
    }
}

function addThought(text) {
    const history = document.getElementById('chat-history');
    const details = document.createElement('details');
    details.className = 'thought-bubble';
    details.style.marginBottom = '10px';
    details.style.color = 'var(--text-sub)';
    details.style.fontSize = '0.8rem';

    const summary = document.createElement('summary');
    summary.innerText = '🤔 생각하기 과정 보기';
    summary.style.cursor = 'pointer';
    summary.style.outline = 'none';

    const content = document.createElement('div');
    content.innerText = text;
    content.style.padding = '10px';
    content.style.background = 'rgba(0,0,0,0.2)';
    content.style.borderRadius = '10px';
    content.style.marginTop = '5px';
    content.style.whiteSpace = 'pre-wrap';

    details.appendChild(summary);
    details.appendChild(content);
    history.appendChild(details);
    history.scrollTop = history.scrollHeight;
}

// --- Character Animation (Wander) ---
function startWandering() {
    const char = document.getElementById('main-char-display');
    if (!char) return;

    function move() {
        // Random position within container (simple translateX)
        // Container width approx 500px? Let's assume +/- 50px from center or random percentage.
        // Actually, frame width is unknown. Let's use % translation.
        const randomX = Math.floor(Math.random() * 100) - 50; // -50% to 50%
        const randomY = Math.floor(Math.random() * 20) - 10;  // small bounce
        const duration = 2000 + Math.random() * 3000;

        char.style.transition = `transform ${duration}ms ease-in-out`;
        char.style.transform = `translate(${randomX}px, ${randomY}px)`;

        // Flip image if moving left/right (optional)
        if (randomX < 0) char.style.transform += " scaleX(-1)";
        else char.style.transform += " scaleX(1)";

        setTimeout(move, duration);
    }
    move();
}

// init call
document.addEventListener('DOMContentLoaded', () => {
    init(); // Existing init
    startWandering();
});

function addMessage(role, text) {
    const history = document.getElementById('chat-history');
    const div = document.createElement('div');
    div.className = `message ${role}`;
    div.innerText = text; // simple text
    history.appendChild(div);
    history.scrollTop = history.scrollHeight;
}

// --- Schedule Data ---
let scheduleData = [];

function addSchedule(task) {
    scheduleData.push(task);
    renderSchedule();
}

function renderSchedule() {
    const list = document.getElementById('schedule-list');
    if (!list) return;

    if (scheduleData.length === 0) {
        list.innerHTML = '<div style="text-align:center; padding: 20px; color: var(--text-sub);">등록된 일정이 없습니다.</div>';
        return;
    }

    list.innerHTML = scheduleData.map(t => `
        <div class="quest-card" style="margin-bottom: 10px; padding: 10px;">
            <div style="font-weight:bold; color:var(--text-main);">${t.content}</div>
            <div style="font-size:0.8rem; color:var(--accent);">
                <i class="fas fa-clock"></i> ${t.time || "시간 미정"} 
                <span style="margin-left:5px;"><i class="fas fa-map-marker-alt"></i> ${t.location || "장소 미정"}</span>
            </div>
        </div>
    `).join('');
}

// --- Schedule Modal ---
function showScheduleModal() {
    document.getElementById('schedule-modal-overlay').style.display = 'flex';
    renderSchedule();
}

function closeScheduleModal() {
    document.getElementById('schedule-modal-overlay').style.display = 'none';
}

// --- Voice Interaction ---
let isVoiceActive = false;
let recognition = null;

function toggleVoice() {
    isVoiceActive = !isVoiceActive;
    const btn = document.getElementById('voice-btn');

    if (isVoiceActive) {
        btn.classList.add('active');
        btn.innerHTML = '<i class="fas fa-microphone"></i>';
        startListening();
        speak("음성 인식이 활성화되었습니다.");
    } else {
        btn.classList.remove('active');
        btn.innerHTML = '<i class="fas fa-microphone-slash"></i>';
        stopListening();
    }
}

function startListening() {
    if (!('webkitSpeechRecognition' in window)) {
        alert("이 브라우저는 음성 인식을 지원하지 않습니다.");
        isVoiceActive = false;
        return;
    }

    recognition = new webkitSpeechRecognition();
    recognition.lang = 'ko-KR';
    recognition.continuous = false; // Turn off for "Wait for Hey Dev" logic sim
    recognition.interimResults = false;

    recognition.onresult = function (event) {
        const transcript = event.results[0][0].transcript;
        console.log("Voice Input:", transcript);

        // Simple "Hey Dev" check or just direct input
        // If strict wake word needed: if (transcript.includes("데브") || transcript.includes("Dev")) ...
        // For usability, let's treat all input as command if Voice Mode is ON.
        document.getElementById('chat-input').value = transcript;
        sendMessage();
    };

    recognition.onend = function () {
        if (isVoiceActive) {
            // Restart listening unless speaking
            if (!window.speechSynthesis.speaking) {
                recognition.start();
            } else {
                // Check again later
                setTimeout(() => { if (isVoiceActive) recognition.start(); }, 1000);
            }
        }
    };

    recognition.start();
}

function stopListening() {
    if (recognition) recognition.stop();
}

function speak(text) {
    if (!isVoiceActive) return;

    // Clean text (remove URLs, code blocks) for TTS
    const cleanText = text.replace(/http\S+|`{3}[\s\S]*?`{3}|`(.+?)`/g, '$1');

    const utterance = new SpeechSynthesisUtterance(cleanText);
    utterance.lang = 'ko-KR';
    utterance.rate = 1.0;
    window.speechSynthesis.speak(utterance);
}



// --- Stats & Charts ---
let postureChart, focusChart;

function showStats() {
    document.getElementById('stats-modal-overlay').style.display = 'flex';
    renderCharts();
}

function closeStatsModal() {
    document.getElementById('stats-modal-overlay').style.display = 'none';
}

function renderCharts() {
    // Mock Data for Demo (Real data would come from server/db)
    const ctx1 = document.getElementById('postureChart').getContext('2d');
    const ctx2 = document.getElementById('focusChart').getContext('2d');

    if (postureChart) postureChart.destroy();
    if (focusChart) focusChart.destroy();

    postureChart = new Chart(ctx1, {
        type: 'line',
        data: {
            labels: ['10분전', '8분전', '6분전', '4분전', '2분전', '현재'],
            datasets: [{
                label: '자세 점수 (낮을수록 좋음)',
                data: [0.1, 0.12, 0.08, 0.15, 0.14, 0.1],
                borderColor: '#63b3ed',
                tension: 0.4
            }]
        }
    });

    focusChart = new Chart(ctx2, {
        type: 'doughnut',
        data: {
            labels: ['집중', '휴식', '딴짓'],
            datasets: [{
                data: [65, 20, 15],
                backgroundColor: ['#68d391', '#63b3ed', '#fc8181']
            }]
        }
    });
}

// Modal
function showModal(title, msg, hasDetails = false) {
    document.getElementById('modal-title').innerText = title;
    document.getElementById('modal-message').innerText = msg;

    if (!hasDetails) {
        document.getElementById('quest-details').style.display = 'none';
    }
    document.getElementById('modal-overlay').style.display = 'flex';
}

function closeModal() {
    document.getElementById('modal-overlay').style.display = 'none';
}

// Start
init();

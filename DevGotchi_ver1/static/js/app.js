
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
        document.getElementById('xp-bar').style.width = data.level_progress + '%';
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
        }
        mainChar.innerText = emoji;
        if (document.getElementById('char-emoji')) document.getElementById('char-emoji').innerText = emoji;


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
        addMessage("assistant", data.response);
    }
}

function addMessage(role, text) {
    const history = document.getElementById('chat-history');
    const div = document.createElement('div');
    div.className = `message ${role}`;
    div.innerText = text; // simple text
    history.appendChild(div);
    history.scrollTop = history.scrollHeight;
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

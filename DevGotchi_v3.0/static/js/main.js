// main.js

// Global State
let timerInterval = null;
let timerSeconds = 0;
let timerRunning = false;
let isMenuOpen = false;
let statsPage = 1;
let lastLevel = null;

document.addEventListener('DOMContentLoaded', () => {
    updateClock();
    setInterval(updateClock, 1000);
    fetchStatus();
    setInterval(fetchStatus, 1000);  // 1초마다 업데이트 (실시간 UI 반영)
    checkTimerState(); // Init Timer Check

    // 캐릭터 클릭 시 메뉴 열기
    const charContainer = document.getElementById('character-container');
    if (charContainer) {
        charContainer.addEventListener('click', (e) => {
            if (!isMenuOpen) {
                openMenu();
                e.stopPropagation();
            }
        });
    }

    // 메뉴 바깥 클릭 시 닫기
    document.addEventListener('click', (e) => {
        if (isMenuOpen && !e.target.closest('.menu-item')) {
            closeMenu();
        }
    });

    // 상태 버튼 토글 (업무중 -> 자리비움 -> 회의중 -> 퇴근)
    const statusBtn = document.getElementById('status-btn');
    if (statusBtn) {
        statusBtn.addEventListener('click', () => {
            const statuses = ["업무중", "자리비움", "회의중", "퇴근"];
            let current = statusBtn.textContent.trim();
            let nextIdx = (statuses.indexOf(current) + 1) % statuses.length;

            if (nextIdx === -1) nextIdx = 0;
            let next = statuses[nextIdx];

            fetch('/api/status/update', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ status: next })
            })
                .then(res => res.json())
                .then(data => {
                    // 즉시 UI 업데이트
                    updateStatusUI(data.status);

                    // 즉시 work mode UI 토글
                    const isWorkMode = data.status === "업무중";
                    const topBar = document.querySelector('.top-bar');
                    const workInfo = document.getElementById('work-info-section');

                    if (isWorkMode) {
                        if (topBar) topBar.classList.add('hidden');
                        if (workInfo) workInfo.classList.remove('hidden');
                    } else {
                        if (topBar) topBar.classList.remove('hidden');
                        if (workInfo) workInfo.classList.add('hidden');
                    }

                    // 즉시 gamestate 가져와 퀘스트 등 업데이트
                    fetchStatus();
                    console.log("상태 변경 완료:", data.status);
                })
                .catch(err => console.error("상태 업데이트 실패:", err));
        });
    }

    // 채팅 입력창 엔터키 이벤트
    const chatInput = document.getElementById('chat-input');
    if (chatInput) {
        chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') sendMessage();
        });
    }

    // URL 파라미터에 따른 앱 자동 열기
    const params = new URLSearchParams(window.location.search);
    const app = params.get('app');
    if (app) {
        openApp(app);
    }
});

// --- [추가] 상태 버튼 글자 및 색상 업데이트 함수 ---
function updateStatusUI(status) {
    const statusBtn = document.getElementById('status-btn');
    if (!statusBtn) return;

    statusBtn.textContent = status;

    // 요청하신 색상 적용
    const statusColors = {
        "업무중": "#00d166",   // 초록색
        "퇴근": "#74b9ff",     // 파란색 (Sky Blue)
        "자리비움": "#ffcc00",  // 노란색
        "회의중": "#ffffff"    // 흰색
    };

    statusBtn.style.color = statusColors[status] || "#ffffff";
    statusBtn.style.fontWeight = "bold"; // 가독성을 위해 굵게 설정
}

// 시계 업데이트
function updateClock() {
    const now = new Date();
    const timeStr = now.toLocaleTimeString('ko-KR', { hour12: false, hour: '2-digit', minute: '2-digit' });
    const clockEl = document.getElementById('clock-time');
    if (clockEl) clockEl.textContent = timeStr;

    if (document.getElementById('timer-clock')) {
        document.getElementById('timer-clock').textContent = now.toLocaleTimeString('ko-KR');
    }
}

// 게임 상태 페치 (날씨, 캐릭터 상태, 자세, 퀘스트, 일정)
async function fetchStatus() {
    try {
        const res = await fetch('/api/gamestate');
        const data = await res.json();

        // 0. 상태 버튼 동기화 (새로고침 없이 색상까지 적용)
        if (data.status) {
            updateStatusUI(data.status);
        }

        // 1. 날씨 정보 업데이트
        if (data.weather) {
            const tempEl = document.getElementById('weather-temp');
            if (tempEl) tempEl.innerText = `${data.weather.temp}°C`;
            const descEl = document.getElementById('weather-desc');
            if (descEl) descEl.innerHTML = `<i class="fas fa-cloud"></i> ${data.weather.condition}`;
            const minmaxEl = document.getElementById('temp-minmax');
            if (minmaxEl) minmaxEl.innerText = `${data.weather.max}°C / ${data.weather.min}°C`;
            const feelsEl = document.getElementById('temp-feels');
            if (feelsEl) feelsEl.innerText = `체감온도 ${data.weather.feels_like}°C`;
        }

        // Update HP/EXP/Level UI
        const hpVal = document.getElementById('hp-val');
        const hpBar = document.getElementById('hp-bar');
        const expVal = document.getElementById('exp-val');
        const expBar = document.getElementById('exp-bar');
        const levelVal = document.getElementById('level-val');

        if (hpVal && hpBar) {
            const maxHp = data.max_hp || 100;
            hpVal.textContent = `${Math.round(data.hp)}/${maxHp}`;
            hpBar.style.width = `${(data.hp / maxHp) * 100}%`;
        }
        if (expVal && expBar) {
            const maxExp = data.max_xp || 100;
            expVal.textContent = `${data.xp}/${maxExp}`;
            expBar.style.width = `${(data.xp / maxExp) * 100}%`;
        }
        if (levelVal) {
            levelVal.textContent = data.level || 0;
        }

        if (lastLevel !== null && data.level > lastLevel) {
            alert(`🎉 Level Up! Lv. ${data.level}`);
        }
        lastLevel = data.level;

        // 3. 자세 경고 로직 (ver1 방식으로 수정)
        const postureInd = document.getElementById('posture-indicator');
        const postureText = document.getElementById('posture-text');
        const statusDot = postureInd ? postureInd.querySelector('.status-dot') : null;

        // posture_score와 is_eye_closed 데이터 기반으로 판정
        const isTurtleNeck = data.posture_score && data.posture_score > 0.18;
        const isEyeClosed = data.is_eye_closed;

        // 우선순위: 눈감음 > 거북목 > 바른 자세
        if (isEyeClosed) {
            // 눈감음 상태
            if (postureInd) {
                postureInd.classList.add('bad');
                postureInd.classList.remove('good');
                postureInd.style.borderColor = '#ff4b2b';
                postureInd.style.backgroundColor = 'rgba(255, 75, 43, 0.2)';
            }
            if (postureText) {
                postureText.innerText = '😴 눈감음 상태입니다';
                postureText.style.color = '#ff4b2b';
            }
            if (statusDot) statusDot.style.color = '#ff4b2b';
        } else if (isTurtleNeck) {
            // 거북목 상태
            if (postureInd) {
                postureInd.classList.add('bad');
                postureInd.classList.remove('good');
                postureInd.style.borderColor = '#ff4b2b';
                postureInd.style.backgroundColor = 'rgba(255, 75, 43, 0.2)';
            }
            if (postureText) {
                postureText.innerText = '🐢 거북목 상태입니다';
                postureText.style.color = '#ff4b2b';
            }
            if (statusDot) statusDot.style.color = '#ff4b2b';
        } else {
            // 바른 자세 유지중
            if (postureInd) {
                postureInd.classList.remove('bad');
                postureInd.classList.add('good');
                postureInd.style.borderColor = '#00d166';
                postureInd.style.backgroundColor = 'rgba(0, 209, 102, 0.2)';
            }
            if (postureText) {
                postureText.innerText = '✅ 바른 자세 유지중';
                postureText.style.color = '#00d166';
            }
            if (statusDot) statusDot.style.color = '#00d166';
        }

        // Work Mode UI Toggle (Replace instead of Overlay)
        const topBar = document.querySelector('.top-bar');
        const workInfo = document.getElementById('work-info-section');

        if (data.work_mode) {
            if (topBar && !topBar.classList.contains('hidden')) {
                topBar.classList.add('hidden');
            }
            if (workInfo && workInfo.classList.contains('hidden')) {
                workInfo.classList.remove('hidden');
            }
        } else {
            if (topBar && topBar.classList.contains('hidden')) {
                topBar.classList.remove('hidden');
            }
            if (workInfo && !workInfo.classList.contains('hidden')) {
                workInfo.classList.add('hidden');
            }
        }

        renderQuests(data.quests, data.available_quests);

        const db = document.getElementById('home-dashboard');
        if (db) {
            let html = '';
            const tState = getTimerState();
            if (tState && timerInterval) {
                const timeStr = document.getElementById('timer-display')?.textContent || "Running";
                html += `<div style="display:inline-block; padding: 5px 15px; background: rgba(0,0,0,0.5); border-radius: 20px; color: #fff; margin: 5px;">⏱️ ${timeStr}</div>`;
            }

            if (data.todays_events && data.todays_events.length > 0) {
                const count = data.todays_events.length;
                const first = data.todays_events[0].title;
                html += `<div style="display:inline-block; padding: 5px 15px; background: rgba(187, 134, 252, 0.3); border-radius: 20px; color: #bb86fc; border: 1px solid #bb86fc; margin: 5px;">📅 ${first} ${count > 1 ? `(+${count - 1})` : ''}</div>`;
            }
            db.innerHTML = html;
        }

    } catch (e) {
        console.error("fetchStatus Error:", e);
    }
}

function renderQuests(activeQuests, availableQuests) {
    const availableList = document.getElementById('available-quest-list');
    const activeList = document.getElementById('active-quest-list');
    const availableSection = document.getElementById('available-quest-section');
    const activeSection = document.getElementById('active-quest-section');

    if (!availableList || !activeList) return;

    // Save expanded state
    const expandedIds = [];
    document.querySelectorAll('.quest-card.expanded').forEach(card => {
        expandedIds.push(card.dataset.questIndex + '-' + card.classList.contains('active'));
    });

    // Clear both lists
    availableList.innerHTML = '';
    activeList.innerHTML = '';

    // Hide available quest section if there's an active quest
    if (activeQuests && activeQuests.length > 0) {
        if (availableSection && !availableSection.classList.contains('hidden')) {
            availableSection.classList.add('hidden');
        }
        if (activeSection && activeSection.classList.contains('hidden')) {
            activeSection.classList.remove('hidden');
        }
    } else {
        if (availableSection && availableSection.classList.contains('hidden')) {
            availableSection.classList.remove('hidden');
        }
        if (activeSection && !activeSection.classList.contains('hidden')) {
            activeSection.classList.add('hidden');
        }
    }

    // Render Available Quests
    if (availableQuests && availableQuests.length > 0 && (!activeQuests || activeQuests.length === 0)) {
        availableQuests.forEach((q, idx) => {
            const card = createQuestCard(q, idx, false);
            if (expandedIds.includes(idx + '-false')) {
                card.classList.add('expanded');
            }
            availableList.appendChild(card);
        });
    } else if (!activeQuests || activeQuests.length === 0) {
        availableList.innerHTML = '<div class="quest-empty">현재 선택 가능한 퀘스트가 없습니다.</div>';
    }

    // Render Active Quests
    if (activeQuests && activeQuests.length > 0) {
        activeQuests.forEach((q, idx) => {
            const card = createQuestCard(q, idx, true);
            if (expandedIds.includes(idx + '-true')) {
                card.classList.add('expanded');
            }
            activeList.appendChild(card);
        });
    } else {
        activeList.innerHTML = '<div class="quest-empty">진행 중인 퀘스트가 없습니다.</div>';
    }
}

function createQuestCard(quest, index, isActive) {
    const card = document.createElement('div');
    card.className = 'quest-card' + (isActive ? ' active' : '');
    card.dataset.questIndex = index;

    const progress = quest.progress || 0;
    const target = quest.target_duration || 1;
    const progressPct = Math.min(100, (progress / target) * 100);

    // Difficulty badge class
    const difficultyClass = quest.difficulty === 'Hard' ? 'hard' : 'normal';

    // Format time
    const formatTime = (seconds) => {
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return mins > 0 ? `${mins}분 ${secs}초` : `${secs}초`;
    };

    card.innerHTML = `
        <div class="quest-card-header">
            <div style="flex: 1;">
                <div class="quest-title">
                    ${isActive ? '✅' : '🎯'} ${quest.name}
                </div>
                <div class="quest-description">${quest.description}</div>
                ${isActive ? '' : `<div class="quest-reward">🏆 클리어 조건: ${quest.clear_condition}</div>`}
            </div>
            <div class="quest-difficulty ${difficultyClass}">${quest.difficulty}</div>
        </div>
        
        ${isActive ? `
        <div class="quest-details">
            <div class="quest-detail-row">
                <span class="quest-detail-icon">📌</span>
                <span class="quest-detail-text"><strong>클리어 조건:</strong> ${quest.clear_condition}</span>
            </div>
            <div class="quest-detail-row">
                <span class="quest-detail-icon">🎯</span>
                <span class="quest-detail-text"><strong>목표 시간:</strong> ${formatTime(target)}</span>
            </div>
            <div class="quest-detail-row">
                <span class="quest-detail-icon">⏱️</span>
                <span class="quest-detail-text"><strong>현재 진행:</strong> ${formatTime(Math.floor(progress))}</span>
            </div>
            <div class="quest-detail-row">
                <span class="quest-detail-icon">🏆</span>
                <span class="quest-detail-text"><strong>보상:</strong> ${quest.reward_xp} XP</span>
            </div>
            <div class="quest-progress-bar">
                <div class="quest-progress-fill" style="width: ${progressPct}%"></div>
                <div class="quest-progress-text">진행도: ${Math.floor(progressPct)}%</div>
            </div>
        </div>
        ` : `
        <div style="margin-top: 10px;">
            <span class="quest-reward">💎 +${quest.reward_xp} XP</span>
        </div>
        `}
    `;

    // Click handler
    if (isActive) {
        card.addEventListener('click', () => {
            card.classList.toggle('expanded');
        });
    } else {
        card.addEventListener('click', () => {
            if (confirm(`${quest.name} 퀘스트를 수락하시겠습니까?\n\n난이도: ${quest.difficulty}\n보상: ${quest.reward_xp} XP\n조건: ${quest.clear_condition}`)) {
                acceptQuest(index);
            }
        });
    }

    return card;
}

async function acceptQuest(idx) {
    try {
        await fetch('/api/quest/accept', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ index: idx })
        });
        fetchStatus(); // Refresh immediately
    } catch (e) {
        console.error(e);
    }
}

function openMenu() {
    isMenuOpen = true;
    const menu = document.getElementById('circular-menu');
    menu.classList.add('active');

    const items = menu.querySelectorAll('.menu-item');
    const radius = 180;
    const total = items.length;
    const step = (2 * Math.PI) / total;

    items.forEach((item, idx) => {
        const angle = idx * step - (Math.PI / 2);
        const x = Math.cos(angle) * radius;
        const y = Math.sin(angle) * radius;
        item.style.transform = `translate(calc(-50% + ${x}px), calc(-50% + ${y}px)) scale(1)`;
    });
}

function closeMenu() {
    isMenuOpen = false;
    const menu = document.getElementById('circular-menu');
    menu.classList.remove('active');
    const items = menu.querySelectorAll('.menu-item');
    items.forEach(item => {
        item.style.transform = `translate(-50%, -50%) scale(0)`;
    });
}

function openApp(appId) {
    const appEl = document.getElementById(appId + '-app');
    if (appEl) {
        appEl.classList.remove('hidden');
        if (appId === 'scheduler') {
            if (typeof initCalendar === 'function') initCalendar();
        }
    } else {
        alert("기능 준비중: " + appId);
    }
}

window.closeApp = (appId) => {
    document.getElementById(appId).classList.add('hidden');
};

function getTimerState() {
    const saved = localStorage.getItem('devgotchi_timer');
    return saved ? JSON.parse(saved) : null;
}

function saveTimerState(state) {
    localStorage.setItem('devgotchi_timer', JSON.stringify(state));
}

function clearTimerState() {
    localStorage.removeItem('devgotchi_timer');
}

window.timerAdd = (mins) => {
    if (timerRunning) return;
    timerSeconds += mins * 60;
    updateTimerDisplay();
};

window.timerReset = () => {
    clearInterval(timerInterval);
    timerRunning = false;
    timerSeconds = 0;
    clearTimerState();
    updateTimerDisplay();
};

window.timerStart = (mode) => {
    if (timerRunning) return;
    timerRunning = true;
    const now = Date.now();
    let state = { mode: mode, startAt: now, initialSeconds: timerSeconds };
    if (mode === 'down') {
        state.targetTime = now + (timerSeconds * 1000);
    }
    saveTimerState(state);
    runTimerLoop();
};

function runTimerLoop() {
    if (timerInterval) clearInterval(timerInterval);
    timerInterval = setInterval(() => {
        const state = getTimerState();
        if (!state) {
            clearInterval(timerInterval);
            timerRunning = false;
            return;
        }
        const now = Date.now();
        if (state.mode === 'down') {
            const remaining = Math.ceil((state.targetTime - now) / 1000);
            if (remaining <= 0) {
                timerSeconds = 0;
                timerRunning = false;
                clearInterval(timerInterval);
                clearTimerState();
                alert("Time Up!");
                updateTimerDisplay();
                return;
            }
            timerSeconds = remaining;
        } else {
            const elapsed = Math.floor((now - state.startAt) / 1000);
            timerSeconds = state.initialSeconds + elapsed;
        }
        updateTimerDisplay();
    }, 1000);
}

function checkTimerState() {
    const state = getTimerState();
    if (state) {
        timerRunning = true;
        const now = Date.now();
        if (state.mode === 'down') {
            timerSeconds = Math.ceil((state.targetTime - now) / 1000);
        } else {
            // Count up
            const elapsed = Math.floor((now - state.startAt) / 1000);
            timerSeconds = state.initialSeconds + elapsed;
        }
        updateTimerDisplay();
        runTimerLoop();
    }

    // Start Polling for Voice Timer Commands
    setInterval(pollTimerCommand, 1500);
}

async function pollTimerCommand() {
    try {
        const res = await fetch('/api/timer/pending');
        const data = await res.json();

        if (data.has_command) {
            console.log("[Voice Timer] Command Received:", data);

            // 1. Reset first
            timerReset();

            // 2. Data Parsing
            const mins = parseFloat(data.minutes);
            const mode = data.mode; // 'up', 'down', 'reset'

            if (mode === 'reset') {
                // Already reset above
                return;
            }

            // 3. Set Time
            if (mode === 'up') {
                // For count up, start from the specified minutes
                timerSeconds = mins * 60;
            } else {
                // For count down, simple set
                timerSeconds = mins * 60;
            }
            updateTimerDisplay();

            // 4. Auto Start
            if (data.auto_start) {
                // Slight delay to ensure UI updates
                setTimeout(() => timerStart(mode), 100);
            }
        }
    } catch (e) {
        console.error("Timer Poll Error", e);
    }
}

function updateTimerDisplay() {
    const h = Math.floor(timerSeconds / 3600);
    const m = Math.floor((timerSeconds % 3600) / 60);
    const s = Math.floor(timerSeconds % 60); // Ensure integer
    const display = document.getElementById('timer-display');
    if (display) {
        display.textContent = `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
    }
}

window.sendMessage = async () => {
    const input = document.getElementById('chat-input');
    const text = input.value.trim();
    if (!text) return;
    addMessage(text, 'user');
    input.value = '';
    try {
        const res = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: text, history: [] })
        });
        const data = await res.json();
        addMessage(data.text, 'ai');
    } catch (e) {
        addMessage("오류가 발생했습니다.", 'ai');
    }
};

// Chat History Management
let currentSessionId = null;
let chatSessions = [];

async function loadChatHistory() {
    try {
        const res = await fetch('/api/history');
        const data = await res.json();

        chatSessions = data.sidebar || [];
        currentSessionId = data.current_session_id;

        renderHistoryList();

        // Load current session messages
        if (data.current_messages && data.current_messages.length > 0) {
            const box = document.getElementById('chat-box');
            if (box) {
                box.innerHTML = ''; // Clear initial message
                data.current_messages.forEach(msg => {
                    addMessage(msg.text, msg.type, false); // false = don't save to backend
                });
            }
        }
    } catch (e) {
        console.error('Failed to load chat history', e);
    }

    // Start polling for new voice messages
    if (typeof startVoicePolling === 'function') startVoicePolling();
}

function renderHistoryList() {
    const listEl = document.getElementById('history-list');
    if (!listEl) return;

    if (chatSessions.length === 0) {
        listEl.innerHTML = '<p style="color: #666; text-align: center; padding: 20px;">대화 기록이 없습니다</p>';
        return;
    }

    listEl.innerHTML = '';

    chatSessions.forEach(session => {
        const item = document.createElement('div');
        item.className = 'history-item' + (session.isActive ? ' active' : '');
        item.style.cssText = `
            padding: 10px;
            margin-bottom: 8px;
            background: ${session.isActive ? 'rgba(187, 134, 252, 0.2)' : 'rgba(255,255,255,0.05)'};
            border-radius: 8px;
            cursor: pointer;
            border-left: 3px solid ${session.isPinned ? '#FFD700' : 'transparent'};
            transition: all 0.2s;
        `;

        item.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                <div style="flex: 1; overflow: hidden;" onclick="loadSession(${session.id})">
                    <div style="font-size: 0.85rem; color: #aaa; margin-bottom: 3px;">
                        ${session.isPinned ? '📌 ' : ''}${session.startTime}
                    </div>
                    <div style="color: #fff; font-size: 0.9rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                        ${session.preview}
                    </div>
                </div>
                <div style="display: flex; gap: 5px; margin-left: 5px;">
                    <button onclick="event.stopPropagation(); pinSession(${session.id}, ${!session.isPinned})" 
                            style="background: none; border: none; cursor: pointer; font-size: 1rem; opacity: 0.7;"
                            title="${session.isPinned ? '고정 해제' : '고정'}">
                        ${session.isPinned ? '📌' : '📍'}
                    </button>
                    <button onclick="event.stopPropagation(); deleteSession(${session.id})" 
                            style="background: none; border: none; cursor: pointer; font-size: 1rem; opacity: 0.7; color: #ff4b2b;"
                            title="삭제">
                        🗑️
                    </button>
                </div>
            </div>
        `;

        listEl.appendChild(item);
    });
}

async function loadSession(sessionId) {
    if (sessionId === currentSessionId) return; // Already loaded

    try {
        // [New Logic] Switch session on backend
        const res = await fetch('/api/session/switch', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: sessionId })
        });
        const data = await res.json();

        if (data.status === "success") {
            currentSessionId = sessionId;
            await loadChatHistory(); // Reload to update active state & messages
        } else {
            console.error("Session switch failed:", data);
        }

    } catch (e) {
        console.error('Failed to load session', e);
        alert('세션 로드 실패');
    }
}

async function createNewChat() {
    try {
        const res = await fetch('/api/chat/reset', { method: 'POST' });
        const data = await res.json();

        if (data.status === 'success') {
            currentSessionId = data.new_session_id;

            // Clear chat box
            const box = document.getElementById('chat-box');
            if (box) {
                box.innerHTML = '<div style="margin-bottom: 10px;"><strong>Dev:</strong> 안녕하세요! 무엇을 도와드릴까요?</div>';
            }

            // Reload history to show new session
            await loadChatHistory();
        }
    } catch (e) {
        console.error('Failed to create new chat', e);
        alert('새 채팅 생성 실패');
    }
}

async function pinSession(sessionId, pin) {
    try {
        await fetch('/api/history/pin', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: sessionId, pin: pin })
        });

        await loadChatHistory(); // Reload to update UI
    } catch (e) {
        console.error('Failed to pin session', e);
    }
}

async function deleteSession(sessionId) {
    if (!confirm('이 대화를 삭제하시겠습니까?')) return;

    try {
        await fetch('/api/history/delete', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: sessionId })
        });

        // If deleted current session, create new one
        if (sessionId === currentSessionId) {
            await createNewChat();
        } else {
            await loadChatHistory(); // Reload to update UI
        }
    } catch (e) {
        console.error('Failed to delete session', e);
        alert('세션 삭제 실패');
    }
}

// Poll Voice Messages
let voicePollInterval = null;

function startVoicePolling() {
    if (voicePollInterval) clearInterval(voicePollInterval);
    voicePollInterval = setInterval(pollVoiceMessages, 2000); // 2초마다 확인
}

async function pollVoiceMessages() {
    // 채팅창이 안 떠있으면 폴링 스킵 (리소스 절약)
    const box = document.getElementById('chat-box');
    if (!box || document.getElementById('ai-app').classList.contains('hidden')) return;

    try {
        const res = await fetch('/api/voice_messages');
        const messages = await res.json(); // Array of {text, type}

        if (messages && messages.length > 0) {
            messages.forEach(msg => {
                // UI에만 추가 (이미 백엔드에는 저장됨)
                addMessage(msg.text, msg.type, false);
            });
        }
    } catch (e) {
        console.error("Voice Poll Error", e);
    }
}

function addMessage(text, type, saveToBackend = true) {
    const box = document.getElementById('chat-box');
    if (!box) return;

    const msg = document.createElement('div');
    msg.style.marginBottom = '10px';
    const role = type === 'user' ? 'Me' : (type === 'system' ? 'System' : 'Dev');
    const color = type === 'system' ? '#aaa' : '#fff';
    msg.innerHTML = `<strong style="color: ${color}">${role}:</strong> ${text}`;
    box.appendChild(msg);
    box.scrollTop = box.scrollHeight;
}

window.nextStatsPage = () => {
    if (statsPage < 6) statsPage++;
    updateStatsPage();
}

window.prevStatsPage = () => {
    if (statsPage > 1) statsPage--;
    updateStatsPage();
}

function updateStatsPage() {
    document.getElementById('stats-title').textContent = `통계 (${statsPage}/6)`;
    const titleObj = {
        1: "업무 시간", 2: "업무 시간대 분석", 3: "자세/졸음 통계",
        4: "주간 인사이트", 5: "월간 리포트", 6: "AI 종합 제안"
    };
    document.getElementById('stats-content-title').textContent = titleObj[statsPage] || "통계";
}

window.careAction = (type) => {
    alert("Dev가 좋아합니다! (" + type + ")");
}

let currentYear = new Date().getFullYear();
let currentMonth = new Date().getMonth();
let eventsData = {};

window.initCalendar = async () => {
    await fetchCalendarEvents();
    updateCalendar();

    // [New] Poll for updates every 3 seconds
    setInterval(async () => {
        await fetchCalendarEvents();
        updateCalendar();
    }, 3000);
};

async function fetchCalendarEvents() {
    try {
        const res = await fetch('/api/calendar');
        eventsData = await res.json();
    } catch (e) {
        console.error("Failed to load calendar", e);
    }
}

window.changeMonth = (delta) => {
    currentMonth += delta;
    if (currentMonth > 11) { currentMonth = 0; currentYear++; }
    if (currentMonth < 0) { currentMonth = 11; currentYear--; }
    updateCalendar();
};

function updateCalendar() {
    const grid = document.getElementById('calendar-grid');
    if (!grid) return;
    document.getElementById('cal-month-year').textContent = `${currentYear}년 ${currentMonth + 1}월`;
    grid.innerHTML = '';
    const days = ["일", "월", "화", "수", "목", "금", "토"];
    days.forEach(d => {
        const dh = document.createElement('div');
        dh.className = 'cal-day-header';
        dh.textContent = d;
        grid.appendChild(dh);
    });
    const firstDay = new Date(currentYear, currentMonth, 1).getDay();
    const lastDate = new Date(currentYear, currentMonth + 1, 0).getDate();
    const prevLastDate = new Date(currentYear, currentMonth, 0).getDate();
    for (let i = 0; i < firstDay; i++) {
        const cell = createCell(prevLastDate - firstDay + 1 + i, true);
        grid.appendChild(cell);
    }
    for (let i = 1; i <= lastDate; i++) {
        const cell = createCell(i, false);
        grid.appendChild(cell);
    }
    const totalCells = firstDay + lastDate;
    const nextDays = (totalCells <= 35) ? 35 - totalCells : 42 - totalCells;
    for (let i = 1; i <= nextDays; i++) {
        const cell = document.createElement('div');
        cell.className = 'cal-cell other-month';
        grid.appendChild(cell);
    }
}

function createCell(day, isOther) {
    const cell = document.createElement('div');
    cell.className = `cal-cell ${isOther ? 'other-month' : ''}`;
    const today = new Date();
    if (!isOther && day === today.getDate() && currentMonth === today.getMonth() && currentYear === today.getFullYear()) {
        cell.classList.add('today');
    }
    cell.innerHTML = `<div class="cal-date-num">${day}</div>`;
    if (!isOther) {
        const monStr = String(currentMonth + 1).padStart(2, '0');
        const dayStr = String(day).padStart(2, '0');
        const dateKey = `${currentYear}-${monStr}-${dayStr}`;
        const todaysEvents = eventsData[dateKey] || [];

        todaysEvents.forEach(evt => {
            const evEl = document.createElement('div');
            evEl.className = `cal-event`;
            // Color mapping based on type
            const colorMap = {
                1: '#bb86fc',
                2: '#03dac6',
                3: '#cf6679'
            };
            evEl.style.backgroundColor = colorMap[evt.type] || '#bb86fc';
            evEl.textContent = evt.title;
            cell.appendChild(evEl);
        });

        // Click handler to show event details
        cell.addEventListener('click', () => {
            if (todaysEvents.length > 0) {
                // Show details of all events on this date
                let detailsHTML = `<div style="max-width: 400px; padding: 20px; background: #1e1e2e; border-radius: 10px; color: #fff;">`;
                detailsHTML += `<h3 style="margin-top: 0; color: #bb86fc;">${currentYear}년 ${currentMonth + 1}월 ${day}일 일정</h3>`;

                todaysEvents.forEach((evt, idx) => {
                    const colorMap = {
                        1: '#bb86fc',
                        2: '#03dac6',
                        3: '#cf6679'
                    };
                    const color = colorMap[evt.type] || '#bb86fc';

                    detailsHTML += `
                        <div style="margin-top: 15px; padding: 15px; background: rgba(255,255,255,0.05); border-radius: 8px; border-left: 4px solid ${color};">
                            <div style="font-weight: bold; font-size: 1.1em; margin-bottom: 8px;">${evt.title || '제목 없음'}</div>
                            ${evt.time ? `<div style="margin: 5px 0; font-size: 0.9em;"><i class="fas fa-clock" style="margin-right: 5px; color: ${color};"></i> ${evt.time}</div>` : ''}
                            ${evt.location ? `<div style="margin: 5px 0; font-size: 0.9em;"><i class="fas fa-map-marker-alt" style="margin-right: 5px; color: ${color};"></i> ${evt.location}</div>` : ''}
                            ${evt.description ? `<div style="margin: 5px 0; font-size: 0.9em; color: #ccc;"><i class="fas fa-align-left" style="margin-right: 5px; color: ${color};"></i> ${evt.description}</div>` : ''}
                        </div>
                    `;
                });

                detailsHTML += `</div>`;

                // Create modal overlay
                const modal = document.createElement('div');
                modal.style.cssText = `
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    background: rgba(0,0,0,0.7);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    z-index: 10000;
                `;
                modal.innerHTML = detailsHTML;

                // Close modal on click
                modal.addEventListener('click', () => {
                    document.body.removeChild(modal);
                });

                document.body.appendChild(modal);
            } else {
                // No events, show simple message
                alert(`${currentYear}년 ${currentMonth + 1}월 ${day}일에 등록된 일정이 없습니다.`);
            }
        });
    }
    return cell;
}

// Override openApp to init calendar
const _originalOpenApp = window.openApp || function () { };
// Since we can't easily hook, we redefine openApp entirely if we want, OR
// Modify the openApp definition in the file.
// Since this block is replacing the END of the file, and openApp is defined earlier (line 144), 
// We can't redefine 'openApp' here without potentially conflicts if `let` or `const` used (it was function declaration).
// Function declarations are hoisted. 
// I will REDEFINE it by assigning to window.openApp works if the original was window attached or global.
// In main.js line 144: `function openApp(appId) { ... }`
// Changes to: `window.openApp = ...`
// I will just add the hook here:
window.openApp = (appId) => {
    const appEl = document.getElementById(appId + '-app');
    if (appEl) {
        appEl.classList.remove('hidden');
        if (appId === 'scheduler') {
            // Init calendar logic
            if (typeof initCalendar === 'function') initCalendar();
        } else if (appId === 'ai') {
            // Init chat history
            if (typeof loadChatHistory === 'function') loadChatHistory();
        }
    } else {
        alert("기능 준비중: " + appId);
    }
};

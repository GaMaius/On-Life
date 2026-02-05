// main.js

// Global State
let timerInterval = null;
let timerSeconds = 0;
let timerRunning = false;
let isMenuOpen = false;
let statsPage = 1;

document.addEventListener('DOMContentLoaded', () => {
    updateClock();
    setInterval(updateClock, 1000);
    fetchStatus();
    setInterval(fetchStatus, 5000);

    const charContainer = document.getElementById('character-container');
    if (charContainer) {
        charContainer.addEventListener('click', (e) => {
            if (!isMenuOpen) {
                openMenu();
                e.stopPropagation();
            }
        });
    }

    document.addEventListener('click', (e) => {
        if (isMenuOpen && !e.target.closest('.menu-item')) {
            closeMenu();
        }
    });

    document.querySelectorAll('.menu-item').forEach(item => {
        item.addEventListener('click', (e) => {
            const action = item.getAttribute('data-action');
            closeMenu();
            openApp(action);
            e.stopPropagation();
        });
    });

    const statusBtn = document.getElementById('status-btn');
    if (statusBtn) {
        statusBtn.addEventListener('click', () => {
            const statuses = ["업무중", "자리비움", "회의중", "퇴근"];
            let current = statusBtn.textContent;
            let nextIdx = (statuses.indexOf(current) + 1) % statuses.length;
            let next = statuses[nextIdx];

            statusBtn.textContent = next;

            const overlay = document.getElementById('work-overlay');
            if (next === "업무중") {
                if (overlay) overlay.classList.remove('hidden');
            } else {
                if (overlay) overlay.classList.add('hidden');
            }

            fetch('/api/status/update', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ status: next })
            });
        });
    }

    // Chat Input Enter
    const chatInput = document.getElementById('chat-input');
    if (chatInput) {
        chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') sendMessage();
        });
    }
});

function updateClock() {
    const now = new Date();
    const timeStr = now.toLocaleTimeString('ko-KR', { hour12: false, hour: '2-digit', minute: '2-digit' });
    const clockEl = document.getElementById('clock-time');
    if (clockEl) clockEl.textContent = timeStr;

    if (document.getElementById('timer-clock')) {
        document.getElementById('timer-clock').textContent = now.toLocaleTimeString('ko-KR');
    }
}

// State Tracking
let lastLevel = null;

// Init from URL
document.addEventListener('DOMContentLoaded', () => {
    const params = new URLSearchParams(window.location.search);
    const app = params.get('app');
    if(app) {
        openApp(app);
    }
});

async function fetchStatus() {
    try {
        const res = await fetch('/api/gamestate');
        const data = await res.json();
        
        // 1. Weather
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

        // 2. HP / EXP / Level
        const hpVal = document.getElementById('hp-val');
        if (hpVal) hpVal.innerText = `${Math.floor(data.hp)}/${data.max_hp}`;
        const hpBar = document.getElementById('hp-bar');
        if (hpBar) hpBar.style.width = `${(data.hp / data.max_hp) * 100}%`;
        
        document.getElementById('exp-val').innerText = `${Math.floor(data.xp)} XP`; // Show raw XP
        // EXP bar logic can be added if we know max per level. For now just show text.
        
        // Level Up Check
        if(lastLevel !== null && data.level > lastLevel) {
            alert(`🎉 Level Up! Lv. ${data.level}`);
        }
        lastLevel = data.level;

        // 3. Posture Alert
        const postureInd = document.getElementById('posture-indicator');
        const postureText = document.getElementById('posture-text');
        
        // Using backend duration or score
        if(data.bad_posture_duration > 0 || data.posture_score > 20) {
            postureInd.classList.add('bad');
            postureInd.classList.remove('good');
            postureInd.style.borderColor = '#ff4b2b';
            postureInd.style.backgroundColor = 'rgba(255, 75, 43, 0.2)';
            
            // Text Change
            postureText.innerText = `⚠️ 거북목 주의! (${Math.floor(data.bad_posture_duration)}s)`;
            postureText.style.color = '#ff4b2b';
            
            // Screen Flash
            document.body.style.boxShadow = "inset 0 0 50px rgba(255,0,0,0.5)";
        } else {
            postureInd.classList.remove('bad');
            postureInd.classList.add('good');
            postureInd.style.borderColor = '#00d166';
            postureInd.style.backgroundColor = 'rgba(0, 209, 102, 0.2)';
            postureText.innerText = "바른 자세 유지중";
            postureText.style.color = '#00d166';
            document.body.style.boxShadow = "none";
        }

        // 4. Quest Rendering
        renderQuests(data.quests, data.available_quests);

    } catch (e) {
        console.error(e);
    }
}

function renderQuests(activeQuests, availableQuests) {
    const list = document.getElementById('quest-list');
    if(!list) return;
    list.innerHTML = ''; // Clear
    
    // Active Quests
    if(activeQuests.length > 0) {
        activeQuests.forEach(q => {
            const item = document.createElement('div');
            item.className = 'quest-item';
            const pct = Math.min(100, (q.progress / q.target_duration) * 100);
            
            // Detail click
            item.onclick = () => {
                alert(`[${q.name}]\n난이도: ${q.difficulty}\n조건: ${q.clear_condition}\n설명: ${q.description}`);
            };

            item.innerHTML = `
                <div style="display:flex; justify-content:space-between;">
                    <strong>${q.name}</strong>
                    <small>${Math.floor(q.progress/60)}/${q.target_duration/60}m</small>
                </div>
                <div class="progress-container" style="height: 5px; margin-top: 5px;">
                    <div class="progress-fill" style="width: ${pct}%; background: #bb86fc;"></div>
                </div>
            `;
            list.appendChild(item);
        });
    }
    
    // Available Quests
    // Always show if any available, distinct section
    if(availableQuests && availableQuests.length > 0) {
        const title = document.createElement('h5');
        title.innerText = "📋 퀘스트 선택";
        title.style.margin = "15px 0 5px 0";
        title.style.borderTop = "1px solid rgba(255,255,255,0.1)";
        title.style.paddingTop = "10px";
        list.appendChild(title);
        
        availableQuests.forEach((q, idx) => {
            const item = document.createElement('div');
            item.className = 'quest-item available';
            item.style.border = "1px dashed #777";
            item.style.cursor = "pointer";
            item.style.marginTop = "5px";
            item.style.padding = "5px";
            item.innerHTML = `
                <div>${q.name}</div>
                <small style="color:#aaa;">+${q.reward_xp} XP | ${q.difficulty}</small>
            `;
            item.onclick = (e) => {
                e.stopPropagation();
                if(confirm(`${q.name} 퀘스트를 수락하시겠습니까?\n보상: ${q.reward_xp} XP`)) {
                    acceptQuest(idx);
                }
            };
            list.appendChild(item);
        });
    }
    
    if(activeQuests.length === 0 && (!availableQuests || availableQuests.length === 0)) {
        list.innerHTML = "<div style='color:#777; text-align:center;'>진행 중인 퀘스트 없음</div>";
    }
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
    } else {
        alert("기능 준비중: " + appId);
    }
}

window.closeApp = (appId) => {
    document.getElementById(appId).classList.add('hidden');
};

// Timer Logic
window.timerAdd = (mins) => {
    timerSeconds += mins * 60;
    updateTimerDisplay();
};

window.timerReset = () => {
    clearInterval(timerInterval);
    timerRunning = false;
    timerSeconds = 0;
    updateTimerDisplay();
};

window.timerStart = (mode) => {
    if (timerRunning) return;
    timerRunning = true;

    timerInterval = setInterval(() => {
        if (mode === 'down') {
            if (timerSeconds > 0) timerSeconds--;
            else {
                timerRunning = false;
                clearInterval(timerInterval);
                alert("Time Up!");
            }
        } else {
            timerSeconds++;
        }
        updateTimerDisplay();
    }, 1000);
};

function updateTimerDisplay() {
    const h = Math.floor(timerSeconds / 3600);
    const m = Math.floor((timerSeconds % 3600) / 60);
    const s = timerSeconds % 60;
    const display = document.getElementById('timer-display');
    if (display) {
        display.textContent = `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
    }
}

// AI Chat Logic
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

function addMessage(text, type) {
    const box = document.getElementById('chat-box');
    const msg = document.createElement('div');
    msg.style.marginBottom = '10px';
    const role = type === 'user' ? 'Me' : 'Dev';
    msg.innerHTML = `<strong>${role}:</strong> ${text}`;
    box.appendChild(msg);
    box.scrollTop = box.scrollHeight;
}

// Stats Logic (Pagination)
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
        1: "업무 시간",
        2: "업무 시간대 분석",
        3: "자세/졸음 통계",
        4: "주간 인사이트",
        5: "월간 리포트",
        6: "AI 종합 제안"
    };
    document.getElementById('stats-content-title').textContent = titleObj[statsPage] || "통계";
    // Mock Chart Changes would go here
}

// Care Logic
window.careAction = (type) => {
    alert("Dev가 좋아합니다! (" + type + ")");
}

// Scheduler Logic - Calendar Implementation
let currentYear = new Date().getFullYear();
let currentMonth = new Date().getMonth();
let eventsData = [
    { date: "2026-02-05", title: "가족 식사", type: 1 },
    { date: "2026-02-14", title: "발렌타인 데이", type: 2 },
    { date: "2026-02-20", title: "프로젝트 마감", type: 3 },
    { date: "2026-03-01", title: "삼일절", type: 1 }
];

window.initCalendar = () => {
    updateCalendar();
};

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

    // Headers
    const days = ["일", "월", "화", "수", "목", "금", "토"];
    days.forEach(d => {
        const dh = document.createElement('div');
        dh.className = 'cal-day-header';
        dh.textContent = d;
        grid.appendChild(dh);
    });

    // Days Calculation
    const firstDay = new Date(currentYear, currentMonth, 1).getDay();
    const lastDate = new Date(currentYear, currentMonth + 1, 0).getDate();
    const prevLastDate = new Date(currentYear, currentMonth, 0).getDate();

    // Prev Month Filler
    for (let i = 0; i < firstDay; i++) {
        const cell = createCell(prevLastDate - firstDay + 1 + i, true);
        grid.appendChild(cell);
    }

    // Current Month
    for (let i = 1; i <= lastDate; i++) {
        const cell = createCell(i, false);
        grid.appendChild(cell);
    }

    // Next Month Filler (Fill to 35 or 42 cells)
    const totalCells = firstDay + lastDate;
    const nextDays = (totalCells <= 35) ? 35 - totalCells : 42 - totalCells;

    for (let i = 1; i <= nextDays; i++) {
        // const cell = createCell(i, true); // Optionally show next month days
        // For blank look:
        const cell = document.createElement('div');
        cell.className = 'cal-cell other-month';
        grid.appendChild(cell);
    }
}

function createCell(day, isOther) {
    const cell = document.createElement('div');
    cell.className = `cal-cell ${isOther ? 'other-month' : ''}`;

    const today = new Date();
    // Check if showing previous month's date logic if needed, but here simple assumption for current month highlight
    if (!isOther && day === today.getDate() && currentMonth === today.getMonth() && currentYear === today.getFullYear()) {
        cell.classList.add('today');
    }

    cell.innerHTML = `<div class="cal-date-num">${day}</div>`;

    if (!isOther) {
        // Check Events
        // Note: Months in JS are 0-indexed, but formatted often 01-12
        const monStr = String(currentMonth + 1).padStart(2, '0');
        const dayStr = String(day).padStart(2, '0');
        const dateKey = `${currentYear}-${monStr}-${dayStr}`;

        const todaysEvents = eventsData.filter(e => e.date === dateKey);
        todaysEvents.forEach(evt => {
            const evEl = document.createElement('div');
            evEl.className = `cal-event type-${evt.type}`;
            evEl.textContent = evt.title;
            cell.appendChild(evEl);
        });

        // Add Logic
        cell.addEventListener('click', () => {
            const title = prompt(`${currentMonth + 1}월 ${day}일 일정 추가:`);
            if (title) {
                eventsData.push({
                    date: dateKey,
                    title: title,
                    type: Math.floor(Math.random() * 3) + 1
                });
                updateCalendar();
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
        }
    } else {
        alert("기능 준비중: " + appId);
    }
}

/* main.js */
document.addEventListener('DOMContentLoaded', () => {
    // 1. Initialize Clock
    updateClock();
    setInterval(updateClock, 1000);

    // 2. Initialize Weather
    fetchWeather();
    setInterval(fetchWeather, 600000); // Every 10 mins

    // 3. Initialize Interactions
    initInteractions();

    // 4. Initialize Components (Apps)
    if (window.Components) {
        Components.initTimer();
        Components.initStats();
        Components.initCare();
        Components.initAI();
        Components.initWorkMode();
    }
});

function updateClock() {
    const now = new Date();
    const hours = String(now.getHours()).padStart(2, '0');
    const minutes = String(now.getMinutes()).padStart(2, '0');
    const days = ['일', '월', '화', '수', '목', '금', '토'];
    const dateStr = `${now.getMonth() + 1}월 ${now.getDate()}일 (${days[now.getDay()]})`;

    document.getElementById('clock').textContent = `${hours}:${minutes}`;
    document.getElementById('date').textContent = dateStr;
}

async function fetchWeather() {
    try {
        const res = await fetch('/api/weather');
        const data = await res.json();

        if (data.error) {
            console.error("Weather Error:", data.error);
            return;
        }

        document.getElementById('temp').textContent = `${Math.round(data.temp)}°C`;
        document.getElementById('weather-desc').textContent = data.desc;
        document.getElementById('feels-like').textContent = Math.round(data.feels_like);
        document.getElementById('min-max').textContent = `${Math.round(data.temp_min)}/${Math.round(data.temp_max)}`;

        // Icon mapping (Simple version)
        const iconMap = {
            'Clear': '☀️', 'Clouds': '☁️', 'Rain': '🌧️', 'Snow': '❄️', 'Thunderstorm': '⚡', 'Drizzle': '🌦️', 'Mist': '🌫️'
        };
        const mainWeather = data.desc.includes('맑음') ? 'Clear' :
            data.desc.includes('구름') ? 'Clouds' :
                data.desc.includes('비') ? 'Rain' :
                    data.desc.includes('눈') ? 'Snow' : '☁️';

        document.getElementById('weather-icon').textContent = iconMap[mainWeather] || '🌤️';

    } catch (e) {
        console.error("Fetch Weather Failed", e);
    }
}

function initInteractions() {
    const charContainer = document.getElementById('character-container');
    const menu = document.getElementById('circular-menu');
    const statusBtn = document.getElementById('status-toggle');
    const workToggle = document.getElementById('work-toggle');

    // Toggle Menu
    let isMenuOpen = false;
    charContainer.addEventListener('click', (e) => {
        // Prevent creating menu if specific elements clicked? Handled by bubbling
        if (!isMenuOpen) {
            openMenu();
        } else {
            closeMenu();
        }
    });

    function openMenu() {
        isMenuOpen = true;
        menu.classList.add('open');
        const radius = 160;
        const items = menu.querySelectorAll('.menu-item');
        const total = items.length;
        const startToRight = -Math.PI / 2; // Start from top

        items.forEach((item, index) => {
            const angle = startToRight + (index * (2 * Math.PI / total));
            const x = Math.cos(angle) * radius;
            const y = Math.sin(angle) * radius;
            item.style.transform = `translate(${x}px, ${y}px)`;
        });
    }

    function closeMenu() {
        isMenuOpen = false;
        menu.classList.remove('open');
        const items = menu.querySelectorAll('.menu-item');
        items.forEach(item => {
            item.style.transform = `translate(-50%, -50%) scale(0)`;
        });
    }

    // Close menu when clicking outside
    document.addEventListener('click', (e) => {
        if (isMenuOpen && !charContainer.contains(e.target)) {
            closeMenu();
        }
    });

    // Menu Items
    menu.querySelectorAll('.menu-item').forEach(item => {
        item.addEventListener('click', (e) => {
            e.stopPropagation(); // Prevent menu toggle logic
            const action = item.dataset.action;
            openModal(action);
            closeMenu();
        });
    });

    // Status Toggle
    const statuses = ['자리비움', '회의중', '퇴근', '업무중'];
    let statusIdx = 0;
    statusBtn.addEventListener('click', () => {
        statusIdx = (statusIdx + 1) % statuses.length;
        const newStatus = statuses[statusIdx];
        statusBtn.textContent = newStatus;

        if (newStatus === '업무중') {
            switchMode('work');
        } else {
            // Log status change to backend
            fetch('/api/status', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ status: newStatus })
            });
        }
    });

    // Work Toggle (Back to Idle)
    workToggle.addEventListener('click', () => {
        switchMode('idle');
        statusBtn.textContent = '자리비움'; // Reset to default away
        statusIdx = 0;
    });
}

function switchMode(mode) {
    const idleScreen = document.getElementById('idle-screen');
    const workScreen = document.getElementById('work-screen');

    if (mode === 'work') {
        idleScreen.classList.remove('active');
        workScreen.classList.add('active');
        // Notify Components to start work logic (e.g. posture check)
        if (window.Components) Components.startWorkLoop();
    } else {
        workScreen.classList.remove('active');
        idleScreen.classList.add('active');
        if (window.Components) Components.stopWorkLoop();
    }
}

function openModal(action) {
    const modalMap = {
        'timer': 'timer-modal',
        'stats': 'stats-modal',
        'care': 'care-modal',
        'ai': 'ai-modal'
    };

    const modalId = modalMap[action];
    if (modalId) {
        document.getElementById(modalId).classList.add('active');
    } else {
        alert("기능 준비중입니다: " + action);
    }
}

// Global Modal Close
document.querySelectorAll('.close-modal').forEach(btn => {
    btn.addEventListener('click', () => {
        btn.closest('.modal').classList.remove('active');
    });
});

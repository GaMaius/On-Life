/* components.js */
window.Components = {
    // --- Timer Component ---
    initTimer: () => {
        let seconds = 0;
        let interval = null;
        let isRunning = false;
        let mode = 'countdown'; // 'countdown' or 'countup'
        const display = document.querySelector('.timer-display');
        const beep = new Audio('/static/audio/beep.wav');

        function format(sec) {
            const h = Math.floor(sec / 3600).toString().padStart(2, '0');
            const m = Math.floor((sec % 3600) / 60).toString().padStart(2, '0');
            const s = (sec % 60).toString().padStart(2, '0');
            return `${h}:${m}:${s}`;
        }

        function updateDisplay() {
            // Update individual spans if they exist, or full text
            const h = Math.floor(seconds / 3600).toString().padStart(2, '0');
            const m = Math.floor((seconds % 3600) / 60).toString().padStart(2, '0');
            const s = (seconds % 60).toString().padStart(2, '0');

            const hoursEl = document.getElementById('timer-hours');
            if (hoursEl) {
                document.getElementById('timer-hours').textContent = h;
                document.getElementById('timer-minutes').textContent = m;
                document.getElementById('timer-seconds').textContent = s;
            } else {
                display.textContent = `${h}:${m}:${s}`;
            }
        }

        function stop() {
            clearInterval(interval);
            isRunning = false;
        }

        function triggerAlarm() {
            stop();
            if (display) display.style.color = 'red'; // Flash red
            beep.play().catch(e => console.log(e));
            setTimeout(() => { if (display) display.style.color = ''; }, 3000);
        }

        const btnCountdown = document.getElementById('btn-countdown');
        if (btnCountdown) btnCountdown.addEventListener('click', () => {
            if (isRunning) stop();
            mode = 'countdown';
            isRunning = true;
            interval = setInterval(() => {
                if (seconds > 0) {
                    seconds--;
                    updateDisplay();
                } else {
                    triggerAlarm();
                }
            }, 1000);
        });

        const btnCountup = document.getElementById('btn-countup');
        if (btnCountup) btnCountup.addEventListener('click', () => {
            if (isRunning) stop();
            mode = 'countup';
            isRunning = true;
            interval = setInterval(() => {
                seconds++;
                updateDisplay();
            }, 1000);
        });

        const btnReset = document.getElementById('btn-reset');
        if (btnReset) btnReset.addEventListener('click', () => {
            stop();
            seconds = 0;
            updateDisplay();
            if (display) display.style.color = '';
        });

        document.querySelectorAll('.preset-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                if (!isRunning) {
                    seconds += parseInt(btn.dataset.time);
                    updateDisplay();
                }
            });
        });
    },

    // --- Stats Component ---
    initStats: () => {
        const carousel = document.querySelector('.stats-carousel');
        const dots = document.querySelectorAll('.pagination .dot');
        const pages = document.querySelectorAll('.stats-page');
        let currentPage = 1;

        function showPage(page) {
            pages.forEach(p => p.classList.remove('active'));
            dots.forEach(d => d.classList.remove('active'));

            const targetPage = document.querySelector(`.stats-page[data-page="${page}"]`);
            const targetDot = document.querySelector(`.dot[data-target="${page}"]`);

            if (targetPage) targetPage.classList.add('active');
            if (targetDot) targetDot.classList.add('active');
            currentPage = page;
        }

        dots.forEach(dot => {
            dot.addEventListener('click', () => {
                showPage(parseInt(dot.dataset.target));
            });
        });

        // Mock Chart Rendering for Page 1
        const chartContainer = document.getElementById('chart-weekly-hours');
        if (chartContainer) {
            // Simple CSS bars
            const data = [4.3, 3.5, 4.0, 3.5, 2.0]; // Mon-Fri
            const max = 5.0;
            let html = '';
            data.forEach((val, i) => {
                const h = (val / max) * 100;
                html += `<div style="display:flex; flex-direction:column; align-items:center; gap:5px;">
                            <div style="width:40px; height:200px; background:#333; border-radius:5px; position:relative; overflow:hidden;">
                                <div style="position:absolute; bottom:0; padding: 0; width:100%; height:${h}%; background:#feca57;"></div>
                            </div>
                            <span>${val}h</span>
                         </div>`;
            });
            chartContainer.innerHTML = `<div style="display:flex; justify-content:space-around; align-items:flex-end; height:100%;">${html}</div>`;
        }
    },

    // --- Care Component ---
    initCare: () => {
        let happiness = 80;
        const happinessBar = document.querySelector('.progress-bar.happiness .fill');
        const happinessVal = document.getElementById('happiness-val');

        function updateHappiness(amount) {
            happiness = Math.min(100, Math.max(0, happiness + amount));
            if (happinessBar) happinessBar.style.width = `${happiness}%`;
            if (happinessVal) happinessVal.textContent = `${happiness}/100`;

            // Animation
            const char = document.querySelector('.care-character img');
            if (char) {
                char.style.transform = 'scale(1.1)';
                setTimeout(() => char.style.transform = 'scale(1)', 200);
            }

            // Sync with backend
            fetch('/api/status', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ happiness: happiness })
            });
        }

        document.querySelectorAll('.care-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                // Determine amount based on type
                const type = btn.dataset.type;
                const gain = type === 'feed' ? 5 : type === 'water' ? 3 : type === 'pet' ? 2 : 10;
                updateHappiness(gain);
            });
        });
    },

    // --- AI Component ---
    initAI: () => {
        const input = document.getElementById('ai-input');
        const sendBtn = document.getElementById('ai-send');
        const chatWindow = document.getElementById('ai-chat-window');

        function addMessage(text, type) {
            const div = document.createElement('div');
            div.className = `message ${type}`;
            div.innerHTML = `<div class="bubble">${text}</div>`;
            chatWindow.appendChild(div);
            chatWindow.scrollTop = chatWindow.scrollHeight;
        }

        async function handleSend() {
            const text = input.value.trim();
            if (!text) return;

            addMessage(text, 'user');
            input.value = '';

            // Loading state
            const loading = document.createElement('div');
            loading.className = 'message ai';
            loading.innerHTML = '<div class="bubble">...</div>';
            chatWindow.appendChild(loading);

            // Mock Response
            setTimeout(() => {
                if (loading.parentNode) chatWindow.removeChild(loading);
                addMessage(`Gemini: "${text}"에 대한 답변입니다. (API 연동 필요)`, 'ai');
            }, 1000);
        }

        if (sendBtn) sendBtn.addEventListener('click', handleSend);
        if (input) input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') handleSend();
        });
    },

    // --- Work Mode ---
    workInterval: null,
    startWorkLoop: function () {
        console.log("Work Mode Started");
        // Simulate Posture Check every 5 seconds
        this.workInterval = setInterval(() => {
            const isBadPosture = Math.random() > 0.8; // 20% chance bad posture
            const indicator = document.querySelector('.posture-indicator');

            if (indicator) {
                if (isBadPosture) {
                    indicator.className = 'posture-indicator bad';
                    indicator.innerHTML = '<i class="fas fa-exclamation-triangle"></i> 거북목 경고!';
                    document.body.style.border = "5px solid red"; // Screen flash
                    setTimeout(() => document.body.style.border = "none", 500);
                } else {
                    indicator.className = 'posture-indicator good';
                    indicator.innerHTML = '<i class="fas fa-check-circle"></i> 바른 자세 유지중';
                }
            }
        }, 5000);
    },
    stopWorkLoop: function () {
        if (this.workInterval) clearInterval(this.workInterval);
        console.log("Work Mode Stopped");
    }
};

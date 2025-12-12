/* --- Global State --- */
const state = {
    currentView: 'dashboard',
    isRecording: false,
    timerInterval: null,
    seconds: 0,
    // History State
    currentDate: new Date(), // Real "Today"
    selectedDate: new Date(), // Navigation cursor
    minDate: new Date(), // -1 Month
    maxDate: new Date(), // +1 Month
};

// Initialize Date Limits (-1 Month to +1 Month)
state.minDate.setMonth(state.minDate.getMonth() - 1);
state.maxDate.setMonth(state.maxDate.getMonth() + 1);

/* --- Mock Data --- */
const mockDB = {
    "2025-12-13": { // Today
        audio: [
            { time: "09:30 AM", len: "04:20" },
            { time: "01:15 PM", len: "01:10" }
        ],
        diary: "Today I felt really productive. The implementation plan for Pana is coming along nicely. I need to focus on the History logic constraint."
    },
    "2025-12-12": { // Yesterday
        audio: [{ time: "08:00 PM", len: "02:00" }],
        diary: "Had a quiet evening. Reflected on the UI designs."
    },
    // Future dates will be empty initially
};

/* --- Navigation Logic --- */
function switchTab(viewName) {
    // 1. Update Sidebar UI
    document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
    // Find the clicked item based on onclick attribute (simple matching)
    const navItems = document.querySelectorAll('.nav-item');
    if(viewName === 'dashboard') navItems[0].classList.add('active');
    if(viewName === 'recordings') navItems[1].classList.add('active');
    if(viewName === 'journal') navItems[2].classList.add('active');
    if(viewName === 'history') {
        navItems[3].classList.add('active');
        renderHistory(); // Refresh history view on enter
    }

    // 2. Switch View Content
    document.querySelectorAll('.view').forEach(el => el.classList.remove('active-view'));
    document.getElementById(viewName).classList.add('active-view');
    
    state.currentView = viewName;
}

/* --- Recordings Logic --- */
const btnRecord = document.getElementById('btn-record');
const btnStop = document.getElementById('btn-stop');
const timerDisplay = document.querySelector('.timer');

btnRecord.addEventListener('click', () => {
    state.isRecording = true;
    btnRecord.disabled = true;
    btnRecord.style.opacity = '0.5';
    btnStop.disabled = false;
    btnStop.classList.add('active');
    
    // Start Timer
    state.seconds = 0;
    state.timerInterval = setInterval(() => {
        state.seconds++;
        const mins = Math.floor(state.seconds / 60).toString().padStart(2, '0');
        const secs = (state.seconds % 60).toString().padStart(2, '0');
        timerDisplay.textContent = `${mins}:${secs}`;
    }, 1000);
});

btnStop.addEventListener('click', () => {
    if(!state.isRecording) return;
    clearInterval(state.timerInterval);
    state.isRecording = false;
    
    // Reset UI
    timerDisplay.textContent = "00:00";
    btnRecord.disabled = false;
    btnRecord.style.opacity = '1';
    btnStop.disabled = true;
    btnStop.classList.remove('active');
    
    alert("Recording Saved! (Simulated)");
});

/* --- Journal Logic --- */
document.getElementById('btn-generate').addEventListener('click', () => {
    const loading = document.getElementById('journal-loading');
    const content = document.getElementById('journal-content');
    
    content.classList.add('hidden');
    loading.classList.remove('hidden');
    
    setTimeout(() => {
        loading.classList.add('hidden');
        content.classList.remove('hidden');
        content.innerHTML = `
            <h3>Summary of the Day</h3>
            <p>Today's recordings suggest a focus on <strong>productivity</strong> and <strong>technical architecture</strong>. You expressed excitement about the new history feature constraints. <br><br> 
            <em>Suggestion:</em> Take a break before starting the styling phase.</p>
        `;
    }, 2000);
});

/* --- History Logic (The Core Task) --- */

// Helper to format YYYY-MM-DD
function formatDateKey(date) {
    return date.toISOString().split('T')[0];
}

function renderHistory() {
    const dateKey = formatDateKey(state.selectedDate);
    const todayKey = formatDateKey(state.currentDate);
    
    // 1. Update Header
    const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
    document.getElementById('hist-date-text').textContent = state.selectedDate.toLocaleDateString('en-US', options);
    
    const statusBadge = document.getElementById('hist-status');
    if (dateKey === todayKey) {
        statusBadge.textContent = "Today";
        statusBadge.className = "badge"; // Default style
        statusBadge.style.display = "inline-block";
    } else if (state.selectedDate > state.currentDate) {
        statusBadge.textContent = "Future Plan";
        statusBadge.className = "badge";
        statusBadge.style.backgroundColor = "#FFF3E0"; // Orange tint
        statusBadge.style.color = "#E65100";
        statusBadge.style.display = "inline-block";
    } else {
        statusBadge.style.display = "none";
    }

    // 2. Handle Navigation Buttons (Constraint Check)
    const prevBtn = document.getElementById('hist-prev');
    const nextBtn = document.getElementById('hist-next');
    
    // Check if previous day is out of bounds
    const prevDay = new Date(state.selectedDate);
    prevDay.setDate(prevDay.getDate() - 1);
    prevBtn.disabled = prevDay < state.minDate;

    // Check if next day is out of bounds
    const nextDay = new Date(state.selectedDate);
    nextDay.setDate(nextDay.getDate() + 1);
    nextBtn.disabled = nextDay > state.maxDate;

    // 3. Render Content
    const audioContainer = document.getElementById('hist-audio-list');
    const diaryContent = document.getElementById('hist-diary-content');
    const futureInput = document.getElementById('hist-future-input');
    const audioSection = document.getElementById('hist-audio-section');
    const diaryTitle = document.getElementById('hist-diary-title');

    const data = mockDB[dateKey] || { audio: [], diary: null };

    // --- FUTURE Logic ---
    if (state.selectedDate > state.currentDate) {
        // Future: Hide Audio, Show Input
        audioSection.style.display = 'none'; // Hide left panel
        diaryTitle.textContent = "Future Notes";
        
        if (data.diary) {
            // If note exists, show it + edit button (simplified to just text here for demo)
            diaryContent.textContent = data.diary;
            diaryContent.style.display = 'block';
            futureInput.classList.add('hidden');
        } else {
            diaryContent.style.display = 'none';
            futureInput.classList.remove('hidden');
            document.getElementById('future-note-text').value = ""; // Clear input
        }
    } 
    // --- PAST / TODAY Logic ---
    else {
        audioSection.style.display = 'flex'; // Show left panel
        diaryTitle.textContent = "Diary Entry";
        futureInput.classList.add('hidden');
        diaryContent.style.display = 'block';

        // Render Audio
        if (data.audio.length > 0) {
            audioContainer.innerHTML = data.audio.map(clip => `
                <div class="audio-row">
                    <div><span class="play-icon">▶</span> Recording ${clip.time}</div>
                    <strong>${clip.len}</strong>
                </div>
            `).join('');
        } else {
            audioContainer.innerHTML = `<p style="color:#aaa; font-style:italic;">No recordings found.</p>`;
        }

        // Render Diary
        diaryContent.textContent = data.diary ? data.diary : "No entry for this day.";
    }
}

function changeHistoryDate(days) {
    const newDate = new Date(state.selectedDate);
    newDate.setDate(newDate.getDate() + days);
    
    // Strict Boundary Check
    if(newDate >= state.minDate && newDate <= state.maxDate) {
        state.selectedDate = newDate;
        renderHistory();
    }
}

function saveFutureNote() {
    const text = document.getElementById('future-note-text').value;
    if(!text) return;
    
    const dateKey = formatDateKey(state.selectedDate);
    
    // Initialize if empty
    if(!mockDB[dateKey]) mockDB[dateKey] = { audio: [], diary: "" };
    
    mockDB[dateKey].diary = text;
    alert("Future note saved to Diary!");
    renderHistory(); // Re-render to show text view
}
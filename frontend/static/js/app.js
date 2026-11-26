// State
let allRecords = [];
let registeredClasses = [];
let lastNotifiedName = null;

// DOM Elements
const timeDisplay = document.getElementById("currentTime");
const modelChip = document.getElementById("modelStatusChip");
const modelText = document.getElementById("modelStatusText");
const statusDot = modelChip.querySelector(".status-dot");
const dateSelector = document.getElementById("dateSelector");
const searchInput = document.getElementById("searchFilter");
const tbody = document.getElementById("attendanceTbody");
const statTotal = document.getElementById("statTotalEnrolled");
const statPresent = document.getElementById("statPresentToday");
const statAbsent = document.getElementById("statAbsent");
const detectionText = document.getElementById("detectionText");
const detectedBanner = document.getElementById("detectedBanner");
const registeredTags = document.getElementById("registeredTags");
const registeredCountBadge = document.getElementById("registeredCountBadge");
const videoFeed = document.getElementById("videoFeed");
const btnRefreshFeed = document.getElementById("btnRefreshFeed");
const btnDownload = document.getElementById("btnDownload");
const toastContainer = document.getElementById("toastContainer");

// Initialize Today Date
function initDates() {
    const today = new Date().toISOString().split("T")[0];
    dateSelector.value = today;
    updateDownloadLink(today);
}

function updateDownloadLink(dateStr) {
    btnDownload.href = `/api/download?date=${dateStr}`;
}

// Live Clock
function updateClock() {
    const now = new Date();
    timeDisplay.textContent = now.toLocaleTimeString();
}
setInterval(updateClock, 1000);
updateClock();

// Reload Video Feed
btnRefreshFeed.addEventListener("click", () => {
    videoFeed.src = "";
    setTimeout(() => {
        videoFeed.src = `/video_feed?t=${Date.now()}`;
    }, 100);
    showToast("Reconnecting video feed...", "info");
});

videoFeed.onerror = () => {
    console.warn("Video feed connection interrupted, retrying in 2s...");
    setTimeout(() => {
        videoFeed.src = `/video_feed?t=${Date.now()}`;
    }, 2000);
};

// Date Selector Changed
dateSelector.addEventListener("change", (e) => {
    const selectedDate = e.target.value;
    updateDownloadLink(selectedDate);
    fetchAttendance(selectedDate);
});

// Search Filter Input
searchInput.addEventListener("input", (e) => {
    const query = e.target.value.toLowerCase().trim();
    renderTable(query);
});

// Toast System
function showToast(message, type = "success") {
    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    
    const icon = type === "success" ? "fa-circle-check" : "fa-bell";
    toast.innerHTML = `<i class="fa-solid ${icon}"></i> <span>${message}</span>`;
    
    toastContainer.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = "0";
        toast.style.transform = "translateX(50px)";
        toast.style.transition = "all 0.3s ease";
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// Check Backend AI Status
async function checkStatus() {
    try {
        const res = await fetch("/api/status");
        const data = await res.json();

        if (data.model_loaded) {
            statusDot.className = "status-dot ready";
            modelText.textContent = "AI Vision Active";
        } else {
            statusDot.className = "status-dot pulsating";
            modelText.textContent = "Loading FaceNet & SVM...";
        }

        if (data.registered_classes && data.registered_classes.length > 0) {
            registeredClasses = data.registered_classes;
            registeredCountBadge.textContent = `${data.total_registered} identities`;
            statTotal.textContent = data.total_registered;
            renderRegisteredTags();
        }

        // Check if recently recognized
        if (data.last_recognition && data.last_recognition.name) {
            detectionText.innerHTML = `Identified: <strong style="color:#34d399">${data.last_recognition.name}</strong> at ${data.last_recognition.time}`;
            
            if (data.last_recognition.is_new && data.last_recognition.name !== lastNotifiedName) {
                lastNotifiedName = data.last_recognition.name;
                showToast(`Attendance marked for ${data.last_recognition.name}!`, "success");
            }
        }
    } catch (err) {
        console.warn("Status check failed:", err);
    }
}

// Render Registered Identity Tags
function renderRegisteredTags() {
    const presentNames = new Set(allRecords.map(r => r.Name));
    registeredTags.innerHTML = registeredClasses.map(name => {
        const isPresent = presentNames.has(name);
        return `
            <span class="person-tag ${isPresent ? 'present' : ''}">
                <i class="fa-solid ${isPresent ? 'fa-check' : 'fa-user'}"></i>
                ${name}
            </span>
        `;
    }).join("");
}

// Fetch Attendance
async function fetchAttendance(dateStr = dateSelector.value) {
    try {
        const res = await fetch(`/api/attendance?date=${dateStr}`);
        const data = await res.json();

        allRecords = data.records || [];
        statPresent.textContent = data.total_present;
        statAbsent.textContent = Math.max(0, (data.total_registered || registeredClasses.length) - data.total_present);

        renderTable(searchInput.value.toLowerCase().trim());
        renderRegisteredTags();
    } catch (err) {
        console.warn("Failed to fetch attendance:", err);
    }
}

// Render Modern Table
function renderTable(filterQuery = "") {
    const filtered = allRecords.filter(r => 
        (r.Name || "").toLowerCase().includes(filterQuery)
    );

    if (filtered.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="5" class="empty-state">
                    <i class="fa-solid fa-inbox"></i>
                    <p>${filterQuery ? 'No matching candidates found.' : 'No attendance records logged for this date.'}</p>
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = filtered.map((record, index) => {
        const initials = record.Name ? record.Name.substring(0, 2).toUpperCase() : "??";
        return `
            <tr>
                <td>${index + 1}</td>
                <td>
                    <div class="candidate-col">
                        <div class="avatar-circle">${initials}</div>
                        <strong>${record.Name}</strong>
                    </div>
                </td>
                <td>${record.Date}</td>
                <td><span style="font-family:monospace; font-weight:600">${record.Time}</span></td>
                <td>
                    <span class="status-badge present">
                        <i class="fa-solid fa-circle-check"></i> Present
                    </span>
                </td>
            </tr>
        `;
    }).join("");
}

// Init & Polling
initDates();
checkStatus();
fetchAttendance();

// Regular background polling
setInterval(checkStatus, 2500);
setInterval(() => fetchAttendance(dateSelector.value), 3000);

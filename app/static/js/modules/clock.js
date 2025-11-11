let hours, minutes, seconds, timeDifference = 0;
const { activeDayName } = window.APP_DATA;

export function highlightCurrentItems() {
    const currentTotalMinutes = hours * 60 + minutes;
    const applyHighlighting = (elements) => {
        if (!elements || elements.length === 0) return;
        elements.forEach(el => el.classList.remove('current-lesson', 'next-lesson'));
        const items = Array.from(elements).map(el => ({ element: el, startMinutes: parseTimeToMinutes(el.dataset.timeStart), endMinutes: parseTimeToMinutes(el.dataset.timeEnd) })).filter(item => item.startMinutes !== null && item.endMinutes !== null);
        let nextStartTime = Infinity;
        items.forEach(item => {
            if (currentTotalMinutes >= item.startMinutes && currentTotalMinutes < item.endMinutes) {
                item.element.classList.add('current-lesson');
            }
            if (item.startMinutes > currentTotalMinutes && item.startMinutes < nextStartTime) {
                nextStartTime = item.startMinutes;
            }
        });
        if (nextStartTime !== Infinity) {
            items.forEach(item => {
                if (item.startMinutes === nextStartTime) {
                    item.element.classList.add('next-lesson');
                }
            });
        }
    };
    const allConsultationRows = [...document.querySelectorAll('#consultations-table-left tr[data-time-start]'), ...document.querySelectorAll('#consultations-table-right tr[data-time-start]')];
    document.querySelectorAll('table[id^="lessons-table-"]').forEach(table => {
        applyHighlighting(table.querySelectorAll('tr[data-time-start]'));
    });
    applyHighlighting(allConsultationRows);
    applyHighlighting(document.querySelectorAll(`#day-${activeDayName} tr[data-time-start]`));
    applyHighlighting(document.querySelectorAll('#consultation-list-display tr[data-time-start]'));
}

function updateClock() {
    const correctedDate = new Date(new Date().getTime() + timeDifference);
    hours = correctedDate.getHours();
    minutes = correctedDate.getMinutes();
    seconds = correctedDate.getSeconds();
    const timeString = `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;

    const timePortrait = document.getElementById('live-time-portrait');
    const timeLandscape = document.getElementById('live-time-landscape');
    if (timePortrait) timePortrait.textContent = timeString;
    if (timeLandscape) timeLandscape.textContent = timeString;

    highlightCurrentItems();
}

export function setupClock(currentTime) {
    const serverTimeParts = currentTime.split(':').map(Number);
    const serverDate = new Date();
    serverDate.setHours(serverTimeParts[0], serverTimeParts[1], serverTimeParts[2]);
    timeDifference = serverDate.getTime() - new Date().getTime();
    updateClock();
    setInterval(updateClock, 1000);
}

function parseTimeToMinutes(timeStr) {
    if (!timeStr || typeof timeStr !== 'string') return null;
    const match = timeStr.match(/(\d{1,2})[.:](\d{2})/);
    return match ? parseInt(match[1], 10) * 60 + parseInt(match[2], 10) : null;
}```

Все, бро. Теперь точно все правильно. Замени эти три файла, и оно заработает.
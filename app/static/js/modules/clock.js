let hours, minutes, seconds, timeDifference = 0;
let loadedDay = null;

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

function setupClock(currentTime) {
    // Если currentTime передается аргументом, используем его, иначе берем из window.APP_DATA
    const timeString = currentTime || window.APP_DATA.currentTime;
    const serverTimeParts = timeString.split(':').map(Number);
    const now = new Date();

    // Склеиваем текущую ДАТУ браузера и ВРЕМЯ сервера
    let serverDate = new Date(now.getFullYear(), now.getMonth(), now.getDate(), serverTimeParts[0], serverTimeParts[1], serverTimeParts[2]);

    // Вычисляем разницу в часах
    const diffInHours = (serverDate.getTime() - now.getTime()) / (1000 * 60 * 60);

    // Защита от "бага полуночи" (когда один день уже сменился, а другой нет)
    if (diffInHours > 12) {
        serverDate.setDate(serverDate.getDate() - 1);
    } else if (diffInHours < -12) {
        serverDate.setDate(serverDate.getDate() + 1);
    }

    timeDifference = serverDate.getTime() - now.getTime();
    
    updateClock();
    setInterval(updateClock, 1000);
}

function updateClock() {
    const correctedDate = new Date(new Date().getTime() + timeDifference);
    const currentDayOfWeek = correctedDate.getDay(); 

    if (loadedDay === null) {
        loadedDay = currentDayOfWeek;
    }

    if (currentDayOfWeek !== loadedDay) {
        console.log("Наступила полночь! Перезагружаю страницу...");
        // ОБЯЗАТЕЛЬНО обновляем переменную до релоада, чтобы разорвать цикл!
        loadedDay = currentDayOfWeek; 
        
        setTimeout(() => {
            window.location.reload(true);
        }, 2000); 
        return; 
    }

    let hours = correctedDate.getHours();
    let minutes = correctedDate.getMinutes();
    let seconds = correctedDate.getSeconds();

    const timeStr = `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;

    const timePortrait = document.getElementById('live-time-portrait');
    const timeLandscape = document.getElementById('live-time-landscape');
    if (timePortrait) timePortrait.textContent = timeStr;
    if (timeLandscape) timeLandscape.textContent = timeStr;

    highlightCurrentItems();
}

function parseTimeToMinutes(timeStr) {
    if (!timeStr || typeof timeStr !== 'string') return null;
    const match = timeStr.match(/(\d{1,2})[.:](\d{2})/);
    return match ? parseInt(match[1], 10) * 60 + parseInt(match[2], 10) : null;
}

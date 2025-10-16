// main.js - Final version with correct keys for portrait mode

document.addEventListener('DOMContentLoaded', () => {
    // --- Константы и переменные ---
    const { activeDayName, currentTime, refreshInterval, scheduleName } = window.APP_DATA;
    const gradeSelector = document.getElementById('grade-selector');
    const classSelector = document.getElementById('class-selector');
    const scheduleDisplay = document.getElementById('schedule-display');
    const resetButton = document.getElementById('reset-button');
    const portraitView = document.querySelector('.portrait-view');
    const sideNavLeft = document.getElementById('side-nav-left');
    const sideNavRight = document.getElementById('side-nav-right');

    const timePortrait = document.getElementById('live-time-portrait');
    const timeLandscape = document.getElementById('live-time-landscape');

    const scheduleContent = document.getElementById('schedule-content');
    const consultationContent = document.getElementById('consultation-content');
    const showScheduleBtn = document.getElementById('show-schedule-btn');
    const showConsultationsBtn = document.getElementById('show-consultations-btn');
    const classSelectionWrapper = document.getElementById('class-selection-wrapper');
    const consultationBackWrapper = document.getElementById('consultation-back-wrapper');
    const backToDaysBtn = document.getElementById('back-to-days-btn');
    const consultationDaySelector = document.getElementById('consultation-day-selector');
    const consultationListDisplay = document.getElementById('consultation-list-display');
    const viewToggleWrapper = document.getElementById('view-toggle-wrapper');

    let fullSchedule = null, allConsultations = null;
    let hours, minutes, seconds, timeDifference = 0;
    const initialScheduleDisplayHTML = scheduleDisplay.innerHTML;
    const STORAGE_KEY_GRADE = 'selectedGrade', STORAGE_KEY_CLASS = 'selectedClass';

    async function main() {
        try {
            [fullSchedule, allConsultations] = await Promise.all([
                fetch(`/api/schedule/${scheduleName}`).then(res => res.json()),
                fetch(`/api/consultations/${scheduleName}`).then(res => res.json())
            ]);
            initializeApp();
        } catch (error) {
            console.error("Critical data loading error:", error);
            scheduleDisplay.innerHTML = `<div class="alert alert-danger text-center">Could not load data.</div>`;
        }
    }

    function initializeApp() {
        portraitView.classList.add('initial-state');

        setupClock();
        setupUI();
        initializeModalHandlers();
        setupConsultationUI();
        restoreUserSelection();
        updateContentSpacer();
        setInterval(() => window.location.reload(true), refreshInterval * 1000);
    }

    function handleSideNavClick() {
        if (portraitView.classList.contains('consultation-day-selected')) {
            showDaySelectorView();
        } else {
            handleReset();
        }
    }

    function setupUI() {
        populateGradeSelector();
        gradeSelector.addEventListener('change', handleGradeChange);
        classSelector.addEventListener('change', handleClassChange);
        resetButton.addEventListener('click', handleReset);
        showScheduleBtn.addEventListener('click', () => togglePortraitView('schedule'));
        showConsultationsBtn.addEventListener('click', () => togglePortraitView('consultations'));

        const panel = document.querySelector('.selection-panel');
        const largePortraitQuery = window.matchMedia('(min-width: 768px) and (min-height: 800px) and (orientation: portrait)');

        if (panel && !largePortraitQuery.matches) {
            new ResizeObserver(updateContentSpacer).observe(panel);
        }

        if (sideNavLeft && sideNavRight) {
            sideNavLeft.addEventListener('click', handleSideNavClick);
        }
    }

    function updateContentSpacer() {
        const panel = document.querySelector('.selection-panel');
        const spacer = document.querySelector('.content-spacer');
        if (!panel || !spacer) return;
        const panelHeight = panel.offsetHeight;
        spacer.style.height = `calc(${panelHeight + 16}px + env(safe-area-inset-bottom))`;
    }

    function togglePortraitView(view) {
        if (view === 'schedule') {
            portraitView.classList.remove('consultation-mode');
            consultationContent.style.display = 'none';
            scheduleContent.style.display = 'flex';
            classSelectionWrapper.style.display = 'block';
            showScheduleBtn.classList.add('btn-primary', 'active');
            showScheduleBtn.classList.remove('btn-secondary');
            showConsultationsBtn.classList.add('btn-secondary');
            showConsultationsBtn.classList.remove('btn-primary', 'active');

            const isClassSelected = !!classSelector.value && classSelector.value !== '--' && !classSelector.disabled;
            portraitView.classList.toggle('initial-state', !isClassSelected);

        } else { // 'consultations'
            portraitView.classList.add('consultation-mode');
            scheduleContent.style.display = 'none';
            consultationContent.style.display = 'flex';
            showDaySelectorView();
            showConsultationsBtn.classList.add('btn-primary', 'active');
            showConsultationsBtn.classList.remove('btn-secondary');
            showScheduleBtn.classList.add('btn-secondary');
            showScheduleBtn.classList.remove('btn-primary', 'active');
            portraitView.classList.remove('schedule-selected');
        }
        setTimeout(updateContentSpacer, 100);
    }

    function setupConsultationUI() {
        const daysOrder = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота"];
        consultationDaySelector.innerHTML = '';
        daysOrder.forEach(day => {
            if (allConsultations[day]?.length > 0) {
                const dayBtn = Object.assign(document.createElement('button'), { className: 'btn day-selector-btn', textContent: day, onclick: () => showConsultationsForDay(day) });
                consultationDaySelector.appendChild(dayBtn);
            }
        });
        backToDaysBtn.addEventListener('click', showDaySelectorView);
    }

    function showConsultationsForDay(day) {
        const consultationsForDay = allConsultations[day];
        if (!consultationsForDay?.length) return;

        portraitView.classList.remove('initial-state');

        let tableHtml = `<div class="schedule-day-card"><div class="schedule-day-header">${day}</div><table class="table table-striped mb-0"><thead><tr><th class="time-col">Время</th><th>Учитель</th><th class="room-col">Кабинет</th></tr></thead><tbody>`;
        consultationsForDay.forEach(c => {
            tableHtml += `<tr data-time-start="${c.start_time || ''}" data-time-end="${c.end_time || ''}"><td class="text-center">${c.time}</td><td>${c.teacher}</td><td class="text-center">${c.room}</td></tr>`;
        });
        tableHtml += `</tbody></table></div>`;
        consultationListDisplay.innerHTML = tableHtml;
        consultationDaySelector.style.display = 'none';
        consultationListDisplay.style.display = 'block';
        classSelectionWrapper.style.display = 'none';
        viewToggleWrapper.style.display = 'none';
        consultationBackWrapper.style.display = 'block';
        portraitView.classList.add('consultation-day-selected');
        highlightCurrentItems();
        scrollToActiveItem('consultation-list-display');
    }

    function showDaySelectorView() {
        consultationListDisplay.style.display = 'none';
        consultationDaySelector.style.display = 'flex';
        consultationBackWrapper.style.display = 'none';
        classSelectionWrapper.style.display = 'none';
        viewToggleWrapper.style.display = 'block';
        portraitView.classList.remove('consultation-day-selected');
        portraitView.classList.add('initial-state');
    }

    function scrollToActiveItem(containerId) {
        setTimeout(() => {
            const container = document.getElementById(containerId);
            if (!container) return;
            const activeItem = container.querySelector('.current-lesson, .next-lesson');
            if (activeItem) activeItem.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }, 100);
    }

    function displayWeekSchedule(selectedClass) {
        portraitView.classList.toggle('schedule-selected', !!selectedClass);

        if (!selectedClass) {
            scheduleDisplay.innerHTML = initialScheduleDisplayHTML;
            scheduleDisplay.classList.add('is-prompting');
            initializeModalHandlers();
            return;
        }

        scheduleDisplay.classList.remove('is-prompting');
        let html = '<div class="row g-4">';
        const daysOrder = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота"];
        daysOrder.forEach(day => {
            const dayData = fullSchedule[day]?.portrait_view[selectedClass];
            html += `<div class="col-12 col-lg-6"><div id="day-${day}" class="schedule-day-card"><div class="schedule-day-header">${day}</div>`;
            if (dayData && dayData.lessons.some(l => l.subject !== '—')) {
                html += '<table class="table table-striped mb-0"><thead><tr><th class="lesson-num-col">№</th><th class="time-col">Время</th><th>Предмет</th><th class="room-col">Каб.</th></tr></thead><tbody>';
                dayData.lessons.forEach(lesson => {
                    // --- ИЗМЕНЕНИЕ ЗДЕСЬ: Используем английские имена полей ---
                    const cabinet = lesson.cabinet || '—';
                    const startTimeAttr = lesson.start_time ? `data-time-start="${lesson.start_time}"` : '';
                    const endTimeAttr = lesson.end_time ? `data-time-end="${lesson.end_time}"` : '';

                    html += `<tr ${startTimeAttr} ${endTimeAttr}>
                                <td class="lesson-num-col">${lesson.lesson_number}</td>
                                <td class="time-col">${lesson.display_time}</td>
                                <td>${lesson.subject}</td>
                                <td class="room-col text-center">${cabinet}</td>
                             </tr>`;
                    // --- КОНЕЦ ИЗМЕНЕНИЯ ---
                });
                html += '</tbody></table>';
            } else {
                html += '<div class="p-4 text-center">В этот день занятий нет.</div>';
            }
            html += '</div></div>';
        });
        html += '</div>';
        scheduleDisplay.innerHTML = html;
        highlightCurrentItems();
        if (isMobileDevice()) scrollToActiveItem('day-' + activeDayName);
    }

    function populateGradeSelector() {
        const grades = new Set();
        Object.values(fullSchedule).forEach(day => {
            if (day?.portrait_view) Object.keys(day.portrait_view).forEach(className => {
                const gradeMatch = className.match(/^\d+/);
                if (gradeMatch) grades.add(gradeMatch[0]);
            });
        });
        Array.from(grades).sort((a, b) => parseInt(a) - parseInt(b)).forEach(grade => gradeSelector.add(new Option(`${grade}-е классы`, grade)));
    }

    function populateClassSelector(selectedGrade) {
        classSelector.innerHTML = '<option selected disabled>--</option>';
        classSelector.disabled = true;
        if (!selectedGrade) return;
        const classNames = new Set();
        Object.values(fullSchedule).forEach(day => {
            if (day?.portrait_view) Object.keys(day.portrait_view).forEach(className => {
                if (className.startsWith(selectedGrade + ' ')) classNames.add(className);
            });
        });
        Array.from(classNames).sort().forEach(name => classSelector.add(new Option(name, name)));
        classSelector.disabled = false;
    }

    function handleGradeChange(e) {
        populateClassSelector(e.target.value);
        classSelector.selectedIndex = 0;
        displayWeekSchedule(null);
        if (isMobileDevice()) {
            localStorage.removeItem(STORAGE_KEY_CLASS);
            localStorage.setItem(STORAGE_KEY_GRADE, e.target.value);
        }
        portraitView.classList.add('initial-state');
    }

    function handleClassChange(e) {
        const selectedClass = e.target.value;
        displayWeekSchedule(selectedClass);
        if (isMobileDevice()) {
            localStorage.setItem(STORAGE_KEY_GRADE, gradeSelector.value);
            localStorage.setItem(STORAGE_KEY_CLASS, selectedClass);
        }
        portraitView.classList.remove('initial-state');
    }

    function handleReset() {
        gradeSelector.selectedIndex = 0;
        classSelector.innerHTML = '<option selected disabled>--</option>';
        classSelector.disabled = true;

        portraitView.classList.remove('consultation-day-selected');
        displayWeekSchedule(null);
        togglePortraitView('schedule');

        if (isMobileDevice()) {
            localStorage.removeItem(STORAGE_KEY_GRADE);
            localStorage.removeItem(STORAGE_KEY_CLASS);
        }
        portraitView.classList.add('initial-state');
    }

    function restoreUserSelection() {
        if (isMobileDevice()) {
            const savedGrade = localStorage.getItem(STORAGE_KEY_GRADE);
            const savedClass = localStorage.getItem(STORAGE_KEY_CLASS);
            if (savedGrade && savedClass) {
                gradeSelector.value = savedGrade;
                populateClassSelector(savedGrade);
                classSelector.value = savedClass;
                displayWeekSchedule(savedClass);
                portraitView.classList.remove('initial-state');
                return true;
            }
        }
        displayWeekSchedule(null);
        return false;
    }

    function setupClock() {
        const serverTimeParts = currentTime.split(':').map(Number);
        const serverDate = new Date();
        serverDate.setHours(serverTimeParts[0], serverTimeParts[1], serverTimeParts[2]);
        timeDifference = serverDate.getTime() - new Date().getTime();
        updateClock();
        setInterval(updateClock, 1000);
    }

    function updateClock() {
        const correctedDate = new Date(new Date().getTime() + timeDifference);
        hours = correctedDate.getHours();
        minutes = correctedDate.getMinutes();
        seconds = correctedDate.getSeconds();
        const timeString = `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;

        if (timePortrait) timePortrait.textContent = timeString;
        if (timeLandscape) timeLandscape.textContent = timeString;

        highlightCurrentItems();
    }

    function highlightCurrentItems() {
        const currentTotalMinutes = hours * 60 + minutes;

        const applyHighlighting = (elements) => {
            if (!elements || elements.length === 0) return;

            elements.forEach(el => el.classList.remove('current-lesson', 'next-lesson'));

            const items = Array.from(elements)
                .map(el => ({
                    element: el,
                    startMinutes: parseTimeToMinutes(el.dataset.timeStart),
                    endMinutes: parseTimeToMinutes(el.dataset.timeEnd)
                }))
                .filter(item => item.startMinutes !== null && item.endMinutes !== null);

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

        const allConsultationRows = [
            ...document.querySelectorAll('#consultations-table-left tr[data-time-start]'),
            ...document.querySelectorAll('#consultations-table-right tr[data-time-start]')
        ];

        document.querySelectorAll('table[id^="lessons-table-"]').forEach(table => {
            applyHighlighting(table.querySelectorAll('tr[data-time-start]'));
        });

        applyHighlighting(allConsultationRows);
        applyHighlighting(document.querySelectorAll(`#day-${activeDayName} tr[data-time-start]`));
        applyHighlighting(document.querySelectorAll('#consultation-list-display tr[data-time-start]'));
    }

    function isMobileDevice() { return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent); }

    function parseTimeToMinutes(timeStr) {
        if (!timeStr || typeof timeStr !== 'string') return null;
        const match = timeStr.match(/(\d{1,2})[.:](\d{2})/);
        return match ? parseInt(match[1], 10) * 60 + parseInt(match[2], 10) : null;
    }

    function initializeModalHandlers() {
        const helpIcon = document.getElementById('help-icon');
        const helpModal = document.getElementById('help-modal');
        const closeModal = document.getElementById('close-modal');
        if (helpIcon && helpModal && closeModal) {
            helpIcon.addEventListener('click', () => { helpModal.style.display = 'flex'; });
            closeModal.addEventListener('click', () => { helpModal.style.display = 'none'; });
            helpModal.addEventListener('click', (e) => { if (e.target === helpModal) helpModal.style.display = 'none'; });
        }
    }

    main();
});
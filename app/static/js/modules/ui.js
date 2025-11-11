import { getFullSchedule, getAllConsultations } from './state.js';
import { setupClock, highlightCurrentItems } from './clock.js';

// --- Константы DOM-элементов ---
const { activeDayName, refreshInterval } = window.APP_DATA;
const gradeSelector = document.getElementById('grade-selector');
const classSelector = document.getElementById('class-selector');
const scheduleDisplay = document.getElementById('schedule-display');
const resetButton = document.getElementById('reset-button');
const portraitView = document.querySelector('.portrait-view');
const sideNavLeft = document.getElementById('side-nav-left');
const sideNavRight = document.getElementById('side-nav-right');
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
const initialScheduleDisplayHTML = scheduleDisplay.innerHTML;
const STORAGE_KEY_GRADE = 'selectedGrade', STORAGE_KEY_CLASS = 'selectedClass';

// --- Главная Экспортируемая Функция ---
export function initializeApp() {
    portraitView.classList.add('initial-state');
    
    setupClock(window.APP_DATA.currentTime);
    setupUI();
    setupGlobalListeners();
    setupConsultationUI();
    
    if (!restoreUserSelection()) {
        animatePromptItems();
    }
    
    updateContentSpacer();
    setInterval(() => window.location.reload(true), refreshInterval * 1000);
}

// --- Все остальные функции - "приватные" помощники ---

function setupGlobalListeners() {
    const helpModal = document.getElementById('help-modal');
    if (!helpModal) return;
    document.body.addEventListener('click', (e) => {
        if (e.target.closest('#help-icon')) {
            helpModal.classList.add('visible');
        } else if (e.target.closest('#close-modal') || e.target === helpModal) {
            helpModal.classList.remove('visible');
        }
    });
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
        sideNavRight.addEventListener('click', handleSideNavClick);
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
        if (!isClassSelected) {
            displayWeekSchedule(null);
        } else {
            highlightCurrentItems();
            if (isMobileDevice()) { scrollToActiveItem('day-' + activeDayName); }
        }
        portraitView.classList.toggle('initial-state', !isClassSelected);
    } else {
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
    const allConsultations = getAllConsultations();
    consultationDaySelector.innerHTML = '';
    daysOrder.forEach((day, index) => {
        if (allConsultations && allConsultations[day]?.length > 0) {
            const dayBtn = Object.assign(document.createElement('button'), {
                className: 'btn day-selector-btn',
                textContent: day,
                onclick: () => showConsultationsForDay(day)
            });
            dayBtn.classList.add('animate-pop-in');
            dayBtn.style.animationDelay = `${index * 80}ms`;
            consultationDaySelector.appendChild(dayBtn);
        }
    });
    backToDaysBtn.addEventListener('click', showDaySelectorView);
}

function showConsultationsForDay(day) {
    const consultationsForDay = getAllConsultations()[day];
    if (!consultationsForDay?.length) return;
    portraitView.classList.remove('initial-state');
    let tableHtml = `<div class="schedule-day-card"><div class="schedule-day-header">${day}</div><table class="table table-striped mb-0"><thead><tr><th class="time-col">Время</th><th>Учитель</th><th class="room-col">Кабинет</th></tr></thead><tbody>`;
    consultationsForDay.forEach(c => {
        tableHtml += `<tr data-time-start="${c.start_time || ''}" data-time-end="${c.end_time || ''}"><td class="text-center">${c.time}</td><td>${c.teacher}</td><td class="text-center">${c.room}</td></tr>`;
    });
    tableHtml += `</tbody></table></div>`;
    consultationListDisplay.innerHTML = tableHtml;
    const card = consultationListDisplay.querySelector('.schedule-day-card');
    if (card) { card.classList.add('animate-fade-in-up'); }
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

function displayWeekSchedule(selectedClass, animate = true) {
    const fullSchedule = getFullSchedule();
    portraitView.classList.toggle('schedule-selected', !!selectedClass);

    if (!selectedClass) {
        const cards = scheduleDisplay.querySelectorAll('.schedule-day-card');
        if (cards.length > 0) {
            cards.forEach((card, index) => {
                card.classList.add('animate-fade-out');
                card.style.animationDelay = `${index * 50}ms`;
            });
            scheduleDisplay.innerHTML = initialScheduleDisplayHTML;
            const newPromptContent = document.getElementById('prompt-content');
            if (newPromptContent) newPromptContent.style.display = 'flex';
            scheduleDisplay.classList.add('is-prompting');
            if (animate) { animatePromptItems(); }
        } else {
            scheduleDisplay.innerHTML = initialScheduleDisplayHTML;
            const newPromptContent = document.getElementById('prompt-content');
            if (newPromptContent) newPromptContent.style.display = 'flex';
            scheduleDisplay.classList.add('is-prompting');
            if (animate) { animatePromptItems(); }
        }
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
                const cabinet = lesson.cabinet || '—';
                const startTimeAttr = lesson.start_time ? `data-time-start="${lesson.start_time}"` : '';
                const endTimeAttr = lesson.end_time ? `data-time-end="${lesson.end_time}"` : '';
                html += `<tr ${startTimeAttr} ${endTimeAttr}><td class="lesson-num-col">${lesson.lesson_number}</td><td class="time-col">${lesson.display_time}</td><td>${lesson.subject}</td><td class="room-col text-center">${cabinet}</td></tr>`;
            });
            html += '</tbody></table>';
        } else {
            html += '<div class="p-4 text-center">В этот день занятий нет.</div>';
        }
        html += '</div></div>';
    });
    html += '</div>';
    scheduleDisplay.innerHTML = html;
    const cards = scheduleDisplay.querySelectorAll('.schedule-day-card');
    cards.forEach((card, index) => {
        card.classList.add('animate-fade-in-up');
        card.style.animationDelay = `${index * 70}ms`;
    });
    highlightCurrentItems();
    if (isMobileDevice()) scrollToActiveItem('day-' + activeDayName);
}

function animatePromptItems() {
    const promptContent = document.getElementById('prompt-content');
    if (!promptContent) return;
    const items = [
        promptContent.querySelector('.prompt-icon'),
        promptContent.querySelector('h3'),
        promptContent.querySelector('p'),
        promptContent.querySelector('.prompt-help')
    ];
    items.forEach((item, index) => {
        if (item) {
            item.classList.add('animate-prompt-item');
            item.style.animationDelay = `${100 + index * 120}ms`;
        }
    });
    const loadingSpinner = document.getElementById('loading-spinner');
    if (loadingSpinner) loadingSpinner.style.display = 'none';
    promptContent.style.display = 'flex';
}

function populateGradeSelector() {
    const fullSchedule = getFullSchedule();
    if (!fullSchedule) return;
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
    const fullSchedule = getFullSchedule();
    classSelector.innerHTML = '<option selected disabled>--</option>';
    classSelector.disabled = true;
    if (!selectedGrade || !fullSchedule) return;
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
    displayWeekSchedule(null, false);
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
    return false;
}

function isMobileDevice() {
    return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
}
// main.js - Полностью переработанная версия

// Ждем, пока загрузится HTML-структура страницы
document.addEventListener('DOMContentLoaded', () => {

    // --- 1. ИСХОДНЫЕ ДАННЫЕ И ПЕРЕМЕННЫЕ ---

    // Получаем базовые данные, переданные из Flask в index.html
    const { activeDayName, currentTime, refreshInterval, scheduleName } = window.APP_DATA;

    // Ссылки на основные элементы интерфейса
    const gradeSelector = document.getElementById('grade-selector');
    const classSelector = document.getElementById('class-selector');
    const scheduleDisplay = document.getElementById('schedule-display');
    const resetButton = document.getElementById('reset-button');
    const portraitView = document.querySelector('.portrait-view');
    const backButtonLeft = document.getElementById('back-button-left');
    const backButtonRight = document.getElementById('back-button-right');
    const timePortrait = document.getElementById('live-time-portrait');
    const timeLandscape = document.getElementById('live-time-landscape');

    // Переменные, которые будут использоваться в разных функциях
    let fullSchedule = null; // Здесь будет храниться загруженное расписание
    let inactivityTimer;     // Для таймера сброса на десктопе
    let hours, minutes, seconds; // Для работы часов

    const initialScheduleDisplayHTML = scheduleDisplay.innerHTML;
    const STORAGE_KEY_GRADE = 'selectedGrade';
    const STORAGE_KEY_CLASS = 'selectedClass';


    // --- 2. ГЛАВНЫЙ ПОТОК ВЫПОЛНЕНИЯ ---

    // Эта функция запускает весь процесс: загружает данные и инициализирует приложение.
    async function main() {
        try {
            // Запрашиваем данные расписания с нашего нового API
            const response = await fetch(`/api/schedule/${scheduleName}`);
            if (!response.ok) {
                throw new Error(`Ошибка сети: ${response.status}`);
            }
            fullSchedule = await response.json();

            // Если данные успешно загружены, запускаем все остальное
            initializeApp();

        } catch (error) {
            console.error("Критическая ошибка при загрузке расписания:", error);
            scheduleDisplay.innerHTML = `<div class="alert alert-danger text-center">Не удалось загрузить данные расписания. Пожалуйста, обновите страницу.</div>`;
        }
    }

    // Эта функция настраивает страницу ПОСЛЕ загрузки данных
    function initializeApp() {
        if (!fullSchedule) return;

        // Настраиваем и запускаем часы
        setupClock();
        // Настраиваем все элементы UI: селекторы, кнопки и их обработчики
        setupUI();
        // Настраиваем модальное окно помощи
        initializeModalHandlers();
        // Восстанавливаем выбор пользователя из памяти, если он есть
        restoreUserSelection();
        // Устанавливаем автообновление страницы
        setInterval(() => { window.location.reload(true); }, refreshInterval * 1000);
    }


    // --- 3. ФУНКЦИИ НАСТРОЙКИ ИНТЕРФЕЙСА (UI) ---

    function setupUI() {
        if (!gradeSelector) return;

        // Заполняем список параллелей
        populateGradeSelector();

        // Вешаем обработчики событий на элементы
        gradeSelector.addEventListener('change', handleGradeChange);
        classSelector.addEventListener('change', handleClassChange);
        resetButton.addEventListener('click', handleReset);
        if (backButtonLeft) backButtonLeft.addEventListener('click', handleReset);
        if (backButtonRight) backButtonRight.addEventListener('click', handleReset);
    }

    function populateGradeSelector() {
        const grades = new Set();
        for (const day in fullSchedule) {
            if (fullSchedule[day]?.portrait_view) {
                for (const className in fullSchedule[day].portrait_view) {
                    const gradeMatch = className.match(/^\d+/);
                    if (gradeMatch) grades.add(gradeMatch[0]);
                }
            }
        }
        Array.from(grades).sort((a, b) => parseInt(a) - parseInt(b)).forEach(grade => {
            gradeSelector.add(new Option(`${grade}-е классы`, grade));
        });
    }

    function populateClassSelector(selectedGrade) {
        classSelector.innerHTML = '<option selected disabled>--</option>';
        classSelector.disabled = true;
        if (!selectedGrade) return;

        const classNames = new Set();
        for (const day in fullSchedule) {
            if (fullSchedule[day]?.portrait_view) {
                for (const className in fullSchedule[day].portrait_view) {
                    if (className.startsWith(selectedGrade + ' ')) {
                        classNames.add(className);
                    }
                }
            }
        }
        Array.from(classNames).sort().forEach(name => {
            classSelector.add(new Option(name, name));
        });
        classSelector.disabled = false;
    }

    function displayWeekSchedule(selectedClass) {
        clearTimeout(inactivityTimer);

        if (!selectedClass) {
            scheduleDisplay.innerHTML = initialScheduleDisplayHTML;
            scheduleDisplay.classList.add('is-prompting');
            portraitView.classList.remove('schedule-selected');
            initializeModalHandlers();
            return;
        }

        portraitView.classList.add('schedule-selected');
        scheduleDisplay.classList.remove('is-prompting');

        let html = '<div class="row g-4">';
        const daysOrder = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота"];

        for (const day of daysOrder) {
            const dayData = fullSchedule[day]?.portrait_view[selectedClass];
            html += `<div class="col-12 col-lg-6"><div id="day-${day}" class="schedule-day-card">`;
            html += `<div class="schedule-day-header">${day}</div>`;

            if (dayData && dayData.lessons.some(l => l.предмет !== '—')) {
                html += '<table class="table table-striped mb-0">';
                html += `<thead><tr><th class="lesson-num-col">№</th><th class="time-col">Время</th><th>Предмет</th></tr></thead><tbody>`;
                dayData.lessons.forEach(lesson => {
                    html += `<tr data-time-start="${lesson.время}"><td class="lesson-num-col">${lesson.урок}</td><td class="time-col">${lesson.время}</td><td>${lesson.предмет}</td></tr>`;
                });
                html += '</tbody></table>';
            } else {
                html += '<div class="p-4 text-center">В этот день занятий нет.</div>';
            }
            html += '</div></div>';
        }
        html += '</div>';
        scheduleDisplay.innerHTML = html;
        highlightCurrentLesson();

        if (!isMobileDevice()) {
            inactivityTimer = setTimeout(() => window.location.reload(), 120000); // 2 минуты
        }

        if (isMobileDevice()) {
            setTimeout(() => {
                const todayCard = document.getElementById(`day-${activeDayName}`);
                if (todayCard) todayCard.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }, 100);
        }
    }

    // --- 4. ОБРАБОТЧИКИ СОБЫТИЙ ---

    function handleGradeChange(e) {
        populateClassSelector(e.target.value);
        classSelector.selectedIndex = 0;
        displayWeekSchedule(null);
        if (isMobileDevice()) {
            localStorage.removeItem(STORAGE_KEY_CLASS);
            localStorage.setItem(STORAGE_KEY_GRADE, e.target.value);
        }
    }

    function handleClassChange(e) {
        const selectedClass = e.target.value;
        displayWeekSchedule(selectedClass);
        if (isMobileDevice()) {
            localStorage.setItem(STORAGE_KEY_GRADE, gradeSelector.value);
            localStorage.setItem(STORAGE_KEY_CLASS, selectedClass);
        }
    }

    function handleReset() {
        clearTimeout(inactivityTimer);
        gradeSelector.selectedIndex = 0;
        classSelector.innerHTML = '<option selected disabled>--</option>';
        classSelector.disabled = true;
        displayWeekSchedule(null);
        if (isMobileDevice()) {
            localStorage.removeItem(STORAGE_KEY_GRADE);
            localStorage.removeItem(STORAGE_KEY_CLASS);
        }
    }


    // --- 5. ЛОГИКА ЧАСОВ И ПОДСВЕТКИ УРОКОВ ---

    function setupClock() {
        [hours, minutes, seconds] = currentTime.split(':').map(Number);
        updateClock(); // Первый запуск, чтобы не было задержки в 1 секунду
        setInterval(updateClock, 1000);
    }

    function updateClock() {
        seconds++;
        if (seconds >= 60) { seconds = 0; minutes++; }
        if (minutes >= 60) { minutes = 0; hours++; }
        if (hours >= 24) { hours = 0; }

        const timeString = `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
        if (timePortrait) timePortrait.textContent = timeString;
        if (timeLandscape) timeLandscape.textContent = timeString;

        // Подсветка урока обновляется каждую секунду вместе с часами
        highlightCurrentLesson();
    }

    function highlightCurrentLesson() {
        const LESSON_DURATION_MIN = 40; // <-- ПОМНИТЕ: это все еще "узкое место"
        const currentTotalMinutes = hours * 60 + minutes;

        const processTable = (table) => {
            if (!table) return;
            const lessonRows = Array.from(table.querySelectorAll('tbody tr[data-time-start]'));
            const lessons = lessonRows
                .map(row => ({
                    element: row,
                    startMinutes: parseTimeToMinutes(row.dataset.timeStart)
                }))
                .filter(lesson => lesson.startMinutes !== null)
                .sort((a, b) => a.startMinutes - b.startMinutes);

            lessons.forEach(lesson => lesson.element.classList.remove('current-lesson', 'next-lesson'));

            let currentLessonFound = false;
            for (const lesson of lessons) {
                const endMinutes = lesson.startMinutes + LESSON_DURATION_MIN;
                if (currentTotalMinutes >= lesson.startMinutes && currentTotalMinutes < endMinutes) {
                    lesson.element.classList.add('current-lesson');
                    currentLessonFound = true;
                    break;
                }
            }

            if (!currentLessonFound) {
                for (const lesson of lessons) {
                    if (lesson.startMinutes > currentTotalMinutes) {
                        lesson.element.classList.add('next-lesson');
                        break;
                    }
                }
            }
        };

        // Обрабатываем таблицы и в портретном, и в ландшафтном режиме
        document.querySelectorAll('#scheduleCarousel table').forEach(processTable);
        const todayCardTable = document.querySelector(`#day-${activeDayName} table`);
        processTable(todayCardTable);
    }


    // --- 6. ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---

    function isMobileDevice() {
        return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
    }

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
            helpModal.addEventListener('click', (e) => {
                if (e.target === helpModal) helpModal.style.display = 'none';
            });
        }
    }

    function restoreUserSelection() {
        if (isMobileDevice()) {
            const savedGrade = localStorage.getItem(STORAGE_KEY_GRADE);
            const savedClass = localStorage.getItem(STORAGE_KEY_CLASS);

            if (savedGrade) {
                gradeSelector.value = savedGrade;
                populateClassSelector(savedGrade);
                if (savedClass) {
                    classSelector.value = savedClass;
                    displayWeekSchedule(savedClass);
                }
            }
        }
    }

    // --- 7. ЗАПУСК ПРИЛОЖЕНИЯ ---
    main();

});
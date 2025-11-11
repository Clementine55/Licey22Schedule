let fullSchedule = null;
let allConsultations = null;

// Функция для сохранения данных
export function setScheduleData(schedule, consultations) {
    fullSchedule = schedule;
    allConsultations = consultations;
}

// Функции для получения данных
export function getFullSchedule() {
    return fullSchedule;
}

export function getAllConsultations() {
    return allConsultations;
}
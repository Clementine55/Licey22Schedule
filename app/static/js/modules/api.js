export async function fetchData(scheduleName) {
    try {
        const [schedule, consultations] = await Promise.all([
            fetch(`/api/schedule/${scheduleName}`).then(res => res.json()),
            fetch(`/api/consultations/${scheduleName}`).then(res => res.json())
        ]);
        return { schedule, consultations };
    } catch (error) {
        console.error("Critical data loading error:", error);
        // Возвращаем null или объект с ошибкой, чтобы главный файл мог это обработать
        return null;
    }
}
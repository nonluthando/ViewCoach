(() => {
    const timer = document.querySelector("[data-interview-timer]");
    if (!timer) {
        return;
    }

    const display = timer.querySelector("[data-timer-display]");
    const startedAt = Date.parse(timer.dataset.startedAt);
    const durationMinutes = Number(timer.dataset.durationMinutes);

    if (!display || Number.isNaN(startedAt) || Number.isNaN(durationMinutes)) {
        return;
    }

    const durationMilliseconds = durationMinutes * 60 * 1000;

    const updateTimer = () => {
        const elapsedMilliseconds = Date.now() - startedAt;
        const remainingMilliseconds = durationMilliseconds - elapsedMilliseconds;
        const isOvertime = remainingMilliseconds < 0;
        const absoluteSeconds = Math.floor(Math.abs(remainingMilliseconds) / 1000);
        const minutes = Math.floor(absoluteSeconds / 60);
        const seconds = absoluteSeconds % 60;

        display.textContent = `${isOvertime ? "+" : ""}${minutes}:${String(seconds).padStart(2, "0")}`;
        timer.classList.toggle("is-overtime", isOvertime);
    };

    updateTimer();
    window.setInterval(updateTimer, 1000);
})();

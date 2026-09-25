(() => {
    const shell = document.querySelector(".app-shell");
    const toggle = document.querySelector("[data-sidebar-toggle]");

    if (!shell || !toggle) {
        return;
    }

    const overlay = shell.querySelector("[data-sidebar-overlay]");

    const close = () => {
        shell.classList.remove("sidebar-open");
        toggle.setAttribute("aria-expanded", "false");
    };

    const open = () => {
        shell.classList.add("sidebar-open");
        toggle.setAttribute("aria-expanded", "true");
    };

    toggle.addEventListener("click", () => {
        if (shell.classList.contains("sidebar-open")) {
            close();
        } else {
            open();
        }
    });

    overlay?.addEventListener("click", close);

    shell.querySelectorAll(".app-sidebar a").forEach((link) => {
        link.addEventListener("click", close);
    });

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
            close();
        }
    });
})();

/* ATLAS personal Watchlist UI */
(function () {
    "use strict";

    function init() {
        const section = document.querySelector("[data-watchlist]");
        if (!section) return;

        const list = section.querySelector("[data-watchlist-list]");
        const input = section.querySelector("[data-watchlist-input]");
        const addButton = section.querySelector("[data-watchlist-add]");
        if (!list || !input || !addButton) return;

        async function refresh() {
            const response = await fetch("/api/watchlist");
            const data = await response.json();
            render(data.symbols || []);
        }

        function render(symbols) {
            list.innerHTML = symbols.map(function (symbol) {
                const href = "/market/" + encodeURIComponent(symbol);
                return `
                    <tr>
                        <td><a href="${href}" class="watchlist-symbol">${escapeHtml(symbol)}</a></td>
                        <td class="watchlist-status">—</td>
                        <td><button type="button" class="watchlist-remove" data-symbol="${escapeHtml(symbol)}" title="Fjern">✕</button></td>
                    </tr>`;
            }).join("");

            list.querySelectorAll(".watchlist-remove").forEach(function (button) {
                button.addEventListener("click", async function () {
                    await fetch("/api/watchlist/" + encodeURIComponent(button.dataset.symbol), { method: "DELETE" });
                    await refresh();
                });
            });
        }

        async function add() {
            const symbol = input.value.trim();
            if (!symbol) return;
            addButton.disabled = true;
            try {
                await fetch("/api/watchlist", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ symbol: symbol })
                });
                input.value = "";
                await refresh();
            } finally {
                addButton.disabled = false;
            }
        }

        addButton.addEventListener("click", add);
        input.addEventListener("keydown", function (event) {
            if (event.key === "Enter") add();
        });
        refresh().catch(function () {});
    }

    function escapeHtml(value) {
        return String(value == null ? "" : value)
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#039;");
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();

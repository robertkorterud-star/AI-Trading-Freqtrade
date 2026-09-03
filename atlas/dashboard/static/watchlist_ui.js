/* ATLAS personal Watchlist UI */
(function () {
    "use strict";

    const STORAGE_KEY = "atlas.watchlist.v1";
    const DEFAULT_SYMBOLS = ["BTC-USD", "ETH-USD", "SOL-USD", "NVDA"];

    function esc(value) {
        return String(value == null ? "" : value)
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#039;");
    }

    function normalize(value) {
        let symbol = String(value || "").trim().toUpperCase();
        if (!symbol) return "";
        symbol = symbol.replaceAll("/", "-");
        if (symbol.endsWith("USDT")) symbol = symbol.slice(0, -4) + "-USD";
        if (symbol.endsWith("USDC")) symbol = symbol.slice(0, -4) + "-USD";
        return symbol;
    }

    function loadSymbols() {
        try {
            const stored = JSON.parse(localStorage.getItem(STORAGE_KEY) || "null");
            if (Array.isArray(stored)) {
                return [...new Set(stored.map(normalize).filter(Boolean))];
            }
        } catch (_) {}
        return [...DEFAULT_SYMBOLS];
    }

    function saveSymbols(symbols) {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(symbols));
    }

    function init() {
        const heading = Array.from(document.querySelectorAll("h2"))
            .find((node) => node.textContent.includes("Watchlist"));
        if (!heading) return;

        const section = heading.closest("section");
        const table = section && section.querySelector("table");
        const tbody = table && table.querySelector("tbody");
        if (!section || !table || !tbody || section.dataset.watchlistReady) return;
        section.dataset.watchlistReady = "1";

        const serverRows = {};
        tbody.querySelectorAll("tr").forEach((row) => {
            const link = row.querySelector("a");
            if (!link) return;
            const symbol = normalize(link.textContent);
            if (!symbol) return;
            const cells = row.querySelectorAll("td");
            serverRows[symbol] = {
                trend: cells[1] ? cells[1].textContent.trim() : "—",
                ai: cells[2] ? cells[2].textContent.trim() : "—",
            };
        });

        const controls = document.createElement("div");
        controls.className = "watchlist-controls";
        controls.innerHTML = `
            <div class="watchlist-search-wrap">
                <input class="watchlist-search" type="text"
                    placeholder="Søk aksje eller krypto, f.eks. BTC, SOL, AAPL…"
                    autocomplete="off">
                <div class="watchlist-suggestions" hidden></div>
            </div>
            <button type="button" class="watchlist-add">＋ Legg til</button>
        `;
        section.insertBefore(controls, table);

        const input = controls.querySelector(".watchlist-search");
        const suggestions = controls.querySelector(".watchlist-suggestions");
        const addButton = controls.querySelector(".watchlist-add");

        function render() {
            const symbols = loadSymbols();
            tbody.innerHTML = symbols.map((symbol) => {
                const info = serverRows[symbol] || {trend: "—", ai: "—"};
                return `
                    <tr>
                        <td>
                            <a href="/market/${encodeURIComponent(symbol)}"
                               class="watchlist-symbol">${esc(symbol)}</a>
                        </td>
                        <td>${esc(info.trend)}</td>
                        <td>
                            ${esc(info.ai)}
                            <button type="button" class="watchlist-remove"
                                    data-symbol="${esc(symbol)}" title="Fjern fra Watchlist">✕</button>
                        </td>
                    </tr>
                `;
            }).join("");

            tbody.querySelectorAll(".watchlist-remove").forEach((button) => {
                button.addEventListener("click", () => {
                    const next = loadSymbols().filter((item) => item !== button.dataset.symbol);
                    saveSymbols(next);
                    render();
                });
            });
        }

        function closeSuggestions() {
            suggestions.hidden = true;
            suggestions.innerHTML = "";
        }

        async function search() {
            const query = input.value.trim();
            if (!query) {
                closeSuggestions();
                return;
            }
            try {
                const response = await fetch("/api/market-search?q=" + encodeURIComponent(query));
                if (!response.ok) throw new Error("search failed");
                const data = await response.json();
                const results = Array.isArray(data.results) ? data.results.slice(0, 8) : [];
                suggestions.innerHTML = results.map((item) => `
                    <button type="button" class="watchlist-suggestion"
                            data-symbol="${esc(item.symbol)}">
                        <strong>${esc(item.symbol)}</strong>
                        <span>${esc(item.name || item.market || "")}</span>
                    </button>
                `).join("");
                suggestions.hidden = results.length === 0;
                suggestions.querySelectorAll(".watchlist-suggestion").forEach((button) => {
                    button.addEventListener("click", () => {
                        input.value = button.dataset.symbol;
                        addSymbol();
                    });
                });
            } catch (_) {
                closeSuggestions();
            }
        }

        function addSymbol() {
            const symbol = normalize(input.value);
            if (!symbol) return;
            const symbols = loadSymbols();
            if (!symbols.includes(symbol)) symbols.push(symbol);
            saveSymbols(symbols);
            input.value = "";
            closeSuggestions();
            render();
        }

        let searchTimer = null;
        input.addEventListener("input", () => {
            window.clearTimeout(searchTimer);
            searchTimer = window.setTimeout(search, 180);
        });
        input.addEventListener("keydown", (event) => {
            if (event.key === "Enter") addSymbol();
            if (event.key === "Escape") closeSuggestions();
        });
        addButton.addEventListener("click", addSymbol);
        document.addEventListener("click", (event) => {
            if (!controls.contains(event.target)) closeSuggestions();
        });

        if (!localStorage.getItem(STORAGE_KEY)) saveSymbols(DEFAULT_SYMBOLS);
        render();
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();

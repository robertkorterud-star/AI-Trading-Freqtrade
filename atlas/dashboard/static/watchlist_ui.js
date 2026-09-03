/* ATLAS personal Watchlist UI */
(function () {
    "use strict";

    const STORAGE_KEY = "atlas.watchlist.v1";
    const MARKET_PATH = "/market/";
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

    function installStyles() {
        if (document.getElementById("atlas-watchlist-styles")) return;
        const style = document.createElement("style");
        style.id = "atlas-watchlist-styles";
        style.textContent = `
            .watchlist-controls {
                display: flex;
                gap: 8px;
                margin: 0 0 14px;
            }
            .watchlist-search-wrap {
                position: relative;
                flex: 1;
            }
            .watchlist-search {
                box-sizing: border-box;
                width: 100%;
                padding: 10px 12px;
                border: 1px solid rgba(56, 189, 248, .28);
                border-radius: 9px;
                background: rgba(15, 23, 42, .85);
                color: white;
                outline: none;
            }
            .watchlist-search:focus {
                border-color: #38bdf8;
            }
            .watchlist-add,
            .market-watchlist-toggle {
                border: 1px solid rgba(56, 189, 248, .45);
                border-radius: 9px;
                padding: 0 14px;
                background: rgba(14, 116, 144, .22);
                color: #7dd3fc;
                font-weight: 700;
                cursor: pointer;
            }
            .watchlist-suggestions {
                position: absolute;
                z-index: 20;
                left: 0;
                right: 0;
                top: calc(100% + 5px);
                overflow: hidden;
                border: 1px solid rgba(148, 163, 184, .25);
                border-radius: 10px;
                background: #111827;
                box-shadow: 0 14px 35px rgba(0, 0, 0, .35);
            }
            .watchlist-suggestion {
                display: flex;
                justify-content: space-between;
                width: 100%;
                padding: 10px 12px;
                border: 0;
                border-bottom: 1px solid rgba(148, 163, 184, .1);
                background: transparent;
                color: white;
                text-align: left;
                cursor: pointer;
            }
            .watchlist-suggestion:hover {
                background: rgba(56, 189, 248, .12);
            }
            .watchlist-suggestion span {
                color: #94a3b8;
            }
            .watchlist-symbol {
                color: white;
                text-decoration: none;
                font-weight: 800;
            }
            .watchlist-symbol:hover {
                color: #38bdf8;
            }
            .watchlist-remove {
                float: right;
                margin-left: 8px;
                border: 0;
                background: transparent;
                color: #64748b;
                cursor: pointer;
            }
            .watchlist-remove:hover {
                color: #f87171;
            }
            .market-watchlist-toggle.is-active {
                border-color: rgba(74, 222, 128, .5);
                color: #86efac;
                background: rgba(22, 101, 52, .2);
            }
            @media (max-width: 600px) {
                .watchlist-controls { flex-direction: column; }
                .watchlist-add { min-height: 40px; }
            }
        `;
        document.head.appendChild(style);
    }

    function initMarketTerminal() {
        if (!window.location.pathname.startsWith(MARKET_PATH)) return;
        if (document.querySelector(".market-watchlist-toggle")) return;

        const actions = document.querySelector(".market-terminal-actions");
        if (!actions) return;

        const match = window.location.pathname.slice(MARKET_PATH.length).split("/")[0];
        const symbol = normalize(decodeURIComponent(match));
        if (!symbol) return;

        const button = document.createElement("button");
        button.type = "button";
        button.className = "market-watchlist-toggle";

        function renderButton() {
            const active = loadSymbols().includes(symbol);
            button.classList.toggle("is-active", active);
            button.setAttribute("aria-pressed", active ? "true" : "false");
            button.textContent = active ? "★ Watchlist" : "☆ Watchlist";
        }

        button.addEventListener("click", function () {
            const symbols = loadSymbols();
            const index = symbols.indexOf(symbol);
            if (index >= 0) {
                symbols.splice(index, 1);
            } else {
                symbols.push(symbol);
            }
            saveSymbols(symbols);
            renderButton();
        });

        actions.insertBefore(button, actions.firstElementChild);
        renderButton();
    }

    function init() {
        const heading = Array.from(document.querySelectorAll("h2"))
            .find((node) => node.textContent.includes("Watchlist"));
        if (!heading) {
            initMarketTerminal();
            return;
        }

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
                        <td><a href="${MARKET_PATH}${encodeURIComponent(symbol)}" class="watchlist-symbol">${esc(symbol)}</a></td>
                        <td>${esc(info.trend)}</td>
                        <td>${esc(info.ai)}
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
                    <button type="button" class="watchlist-suggestion" data-symbol="${esc(item.symbol)}">
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

    installStyles();
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();

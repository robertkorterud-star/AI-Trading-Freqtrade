/* ATLAS personal Watchlist UI */
(function () {
    "use strict";
    function esc(value) { return String(value == null ? "" : value).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#039;"); }
    function init() {
        const heading = Array.from(document.querySelectorAll("h2")).find(n => n.textContent.includes("Watchlist"));
        if (!heading) return;
        const section = heading.closest("section"), table = section && section.querySelector("table"), tbody = table && table.querySelector("tbody");
        if (!section || !table || !tbody || section.dataset.watchlistReady) return;
        section.dataset.watchlistReady = "1";
        const controls = document.createElement("div");
        controls.className = "watchlist-controls";
        controls.innerHTML = '<input type="text" placeholder="Søk symbol, f.eks. BTC-USD eller AAPL" autocomplete="off"><button type="button">＋ Legg til</button>';
        section.insertBefore(controls, table);
        const input = controls.querySelector("input"), add = controls.querySelector("button");
        async function refresh() {
            const r = await fetch("/api/watchlist"); if (!r.ok) throw new Error("Watchlist unavailable");
            render((await r.json()).symbols || []);
        }
        function render(symbols) {
            tbody.innerHTML = symbols.map(s => '<tr><td><a href="/market/' + encodeURIComponent(s) + '" style="color:white;text-decoration:none;font-weight:bold">' + esc(s) + '</a></td><td>—</td><td><button type="button" class="watchlist-remove" data-symbol="' + esc(s) + '">✕</button></td></tr>').join("");
            tbody.querySelectorAll(".watchlist-remove").forEach(b => b.addEventListener("click", async () => { b.disabled = true; await fetch("/api/watchlist/" + encodeURIComponent(b.dataset.symbol), {method:"DELETE"}); await refresh(); }));
        }
        async function addSymbol() {
            const symbol = input.value.trim(); if (!symbol) return; add.disabled = true;
            try { await fetch("/api/watchlist", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({symbol})}); input.value=""; await refresh(); }
            finally { add.disabled = false; }
        }
        add.addEventListener("click", addSymbol); input.addEventListener("keydown", e => { if (e.key === "Enter") addSymbol(); }); refresh().catch(() => {});
    }
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init); else init();
})();

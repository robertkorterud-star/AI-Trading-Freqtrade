/*
 * ATLAS Market Terminal enhancements.
 *
 * 1. Binance crypto pairs are quoted in USDT/USDC. For display-currency
 * conversion those quotes are treated as USD-equivalent, while the chart
 * itself keeps its native market values.
 *
 * 2. Research strategies opens as an overlay on the Market Terminal instead
 * of navigating away from the chart. This keeps the live candlestick chart
 * visible while ATLAS research is displayed.
 */
(function () {
    "use strict";

    // ---------------------------------------------------------
    // FX compatibility: USDT/USDC -> USD for the FX endpoint.
    // ---------------------------------------------------------
    const originalFetch = window.fetch.bind(window);

    window.fetch = function (input, init) {
        try {
            const rawUrl =
                typeof input === "string"
                    ? input
                    : input && input.url;

            if (rawUrl && rawUrl.includes("/api/fx-rate")) {
                const url = new URL(rawUrl, window.location.origin);
                const source = (url.searchParams.get("source") || "")
                    .toUpperCase();

                if (source === "USDT" || source === "USDC") {
                    url.searchParams.set("source", "USD");

                    if (typeof input === "string") {
                        return originalFetch(url.toString(), init);
                    }

                    return originalFetch(
                        new Request(url.toString(), input),
                        init
                    );
                }
            }
        } catch (_) {
            // Fall through to the normal fetch implementation.
        }

        return originalFetch(input, init);
    };


    // ---------------------------------------------------------
    // Research overlay.
    // ---------------------------------------------------------
    function installResearchOverlay() {
        const researchLink = document.querySelector(
            ".market-terminal-research"
        );

        if (!researchLink) {
            return;
        }

        researchLink.addEventListener("click", async function (event) {
            event.preventDefault();

            const href = new URL(
                researchLink.href,
                window.location.origin
            );
            const symbol =
                href.searchParams.get("research") ||
                window.location.pathname.split("/").pop();

            const overlay = document.createElement("div");
            overlay.className = "atlas-research-overlay";
            overlay.innerHTML = `
                <div class="atlas-research-modal" role="dialog" aria-modal="true">
                    <div class="atlas-research-modal-header">
                        <div>
                            <div class="atlas-research-kicker">ATLAS INTELLIGENCE</div>
                            <h2>🧠 Research strategies — ${escapeHtml(symbol)}</h2>
                            <p>Research stays open while the candlestick chart remains visible underneath.</p>
                        </div>
                        <button type="button" class="atlas-research-close" aria-label="Close">×</button>
                    </div>
                    <div class="atlas-research-body">
                        <div class="atlas-research-loading">Loading ATLAS research…</div>
                    </div>
                </div>
            `;

            document.body.appendChild(overlay);
            document.body.classList.add("atlas-research-open");

            const close = function () {
                document.body.classList.remove("atlas-research-open");
                overlay.remove();
            };

            overlay.querySelector(".atlas-research-close")
                .addEventListener("click", close);

            overlay.addEventListener("click", function (clickEvent) {
                if (clickEvent.target === overlay) {
                    close();
                }
            });

            document.addEventListener("keydown", function onKeyDown(keyEvent) {
                if (keyEvent.key === "Escape") {
                    close();
                    document.removeEventListener("keydown", onKeyDown);
                }
            });

            try {
                const response = await originalFetch(
                    "/api/strategy-research?" +
                    new URLSearchParams({ symbol })
                );
                const data = await response.json();

                if (!response.ok) {
                    throw new Error(
                        data.error || "Strategy research unavailable."
                    );
                }

                renderResearch(
                    overlay.querySelector(".atlas-research-body"),
                    data
                );
            } catch (error) {
                overlay.querySelector(".atlas-research-body").innerHTML = `
                    <div class="atlas-research-error">
                        ${escapeHtml(error.message)}
                    </div>
                `;
            }
        });
    }


    function escapeHtml(value) {
        return String(value == null ? "" : value)
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#039;");
    }


    function renderResearch(container, data) {
        const strategies = Array.isArray(data.strategies)
            ? data.strategies
            : [];
        const backtests = Array.isArray(data.backtests)
            ? data.backtests
            : [];

        if (!strategies.length) {
            container.innerHTML = `
                <div class="atlas-research-empty">
                    ATLAS fant ingen strategihypoteser i tilgjengelig research.
                </div>
            `;
            return;
        }

        const backtestFor = function (name) {
            return backtests.find(function (item) {
                return item.strategy_name === name;
            });
        };

        container.innerHTML = `
            <div class="atlas-research-summary">
                <span><strong>${strategies.length}</strong> strategies tested</span>
                <span><strong>${backtests.length}</strong> backtests</span>
                <span>Symbol: <strong>${escapeHtml(data.symbol)}</strong></span>
            </div>

            <div class="atlas-research-grid">
                ${strategies.map(function (strategy) {
                    const backtest = backtestFor(strategy.name);
                    return `
                        <article class="atlas-research-card">
                            <div class="atlas-research-card-kicker">STRATEGY</div>
                            <h3>${escapeHtml(strategy.name)}</h3>

                            <div class="atlas-research-rule">
                                <strong>Timeframe</strong>
                                <span>${escapeHtml(strategy.timeframe)}</span>
                            </div>
                            <div class="atlas-research-rule">
                                <strong>Entry</strong>
                                <span>${escapeHtml(strategy.entry_rule)}</span>
                            </div>
                            <div class="atlas-research-rule">
                                <strong>Exit</strong>
                                <span>${escapeHtml(strategy.exit_rule)}</span>
                            </div>
                            <div class="atlas-research-rule">
                                <strong>Stop loss</strong>
                                <span>${escapeHtml(strategy.stop_loss)}</span>
                            </div>
                            <div class="atlas-research-rule">
                                <strong>Take profit</strong>
                                <span>${escapeHtml(strategy.take_profit)}</span>
                            </div>

                            ${strategy.reasoning && strategy.reasoning.length
                                ? `<div class="atlas-research-reasoning">
                                    <strong>Why ATLAS found this</strong>
                                    <ul>${strategy.reasoning.map(function (reason) {
                                        return `<li>${escapeHtml(reason)}</li>`;
                                    }).join("")}</ul>
                                   </div>`
                                : ""}

                            ${backtest
                                ? `<div class="atlas-research-backtest">
                                    <div class="atlas-research-backtest-title">Backtest — 1 year / 1h</div>
                                    <div class="atlas-research-stats">
                                        <span>Trades <strong>${escapeHtml(backtest.trades)}</strong></span>
                                        <span>Win rate <strong>${escapeHtml(backtest.win_rate)}%</strong></span>
                                        <span>Return <strong>${escapeHtml(backtest.total_return)}%</strong></span>
                                        <span>PF <strong>${escapeHtml(backtest.profit_factor)}</strong></span>
                                        <span>Max DD <strong>${escapeHtml(backtest.max_drawdown)}%</strong></span>
                                    </div>
                                   </div>`
                                : ""}
                        </article>
                    `;
                }).join("")}
            </div>
        `;
    }


    function installStyles() {
        if (document.getElementById("atlas-market-enhancement-styles")) {
            return;
        }

        const style = document.createElement("style");
        style.id = "atlas-market-enhancement-styles";
        style.textContent = `
            body.atlas-research-open { overflow: hidden; }
            .atlas-research-overlay {
                position: fixed;
                inset: 0;
                z-index: 9999;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 24px;
                background: rgba(2, 6, 23, .78);
                backdrop-filter: blur(4px);
            }
            .atlas-research-modal {
                width: min(1180px, 96vw);
                max-height: 92vh;
                overflow: auto;
                border: 1px solid rgba(148, 163, 184, .25);
                border-radius: 18px;
                background: #0f172a;
                box-shadow: 0 24px 80px rgba(0, 0, 0, .45);
                color: #e2e8f0;
            }
            .atlas-research-modal-header {
                display: flex;
                justify-content: space-between;
                gap: 20px;
                padding: 24px 26px 18px;
                border-bottom: 1px solid rgba(148, 163, 184, .16);
            }
            .atlas-research-modal-header h2 { margin: 4px 0 6px; }
            .atlas-research-modal-header p { margin: 0; color: #94a3b8; }
            .atlas-research-kicker,
            .atlas-research-card-kicker {
                font-size: 11px;
                font-weight: 800;
                letter-spacing: .12em;
                color: #38bdf8;
            }
            .atlas-research-close {
                width: 40px;
                height: 40px;
                flex: 0 0 40px;
                border: 1px solid rgba(148, 163, 184, .25);
                border-radius: 10px;
                background: rgba(15, 23, 42, .8);
                color: #e2e8f0;
                font-size: 26px;
                cursor: pointer;
            }
            .atlas-research-body { padding: 22px 26px 28px; }
            .atlas-research-loading,
            .atlas-research-empty,
            .atlas-research-error {
                padding: 24px;
                border-radius: 12px;
                background: rgba(30, 41, 59, .7);
                color: #cbd5e1;
            }
            .atlas-research-error { color: #fca5a5; }
            .atlas-research-summary {
                display: flex;
                flex-wrap: wrap;
                gap: 10px;
                margin-bottom: 18px;
            }
            .atlas-research-summary span {
                padding: 8px 12px;
                border-radius: 999px;
                background: rgba(30, 41, 59, .8);
                color: #94a3b8;
            }
            .atlas-research-summary strong { color: #e2e8f0; }
            .atlas-research-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
                gap: 16px;
            }
            .atlas-research-card {
                padding: 18px;
                border: 1px solid rgba(148, 163, 184, .16);
                border-radius: 14px;
                background: rgba(15, 23, 42, .72);
            }
            .atlas-research-card h3 { margin: 6px 0 16px; }
            .atlas-research-rule {
                display: grid;
                grid-template-columns: 92px 1fr;
                gap: 10px;
                padding: 7px 0;
                border-bottom: 1px solid rgba(148, 163, 184, .09);
            }
            .atlas-research-rule strong { color: #94a3b8; font-size: 12px; }
            .atlas-research-rule span { color: #e2e8f0; }
            .atlas-research-reasoning {
                margin-top: 14px;
                padding: 12px;
                border-radius: 10px;
                background: rgba(30, 41, 59, .6);
            }
            .atlas-research-reasoning ul { margin: 8px 0 0 18px; padding: 0; }
            .atlas-research-reasoning li { margin: 4px 0; color: #cbd5e1; }
            .atlas-research-backtest {
                margin-top: 16px;
                padding-top: 14px;
                border-top: 1px solid rgba(148, 163, 184, .14);
            }
            .atlas-research-backtest-title { font-weight: 700; margin-bottom: 10px; }
            .atlas-research-stats {
                display: grid;
                grid-template-columns: repeat(2, minmax(0, 1fr));
                gap: 8px;
            }
            .atlas-research-stats span {
                padding: 8px;
                border-radius: 8px;
                background: rgba(30, 41, 59, .65);
                color: #94a3b8;
                font-size: 12px;
            }
            .atlas-research-stats strong { display: block; color: #e2e8f0; font-size: 14px; }
            @media (max-width: 700px) {
                .atlas-research-overlay { padding: 8px; }
                .atlas-research-modal-header,
                .atlas-research-body { padding-left: 16px; padding-right: 16px; }
            }
        `;
        document.head.appendChild(style);
    }


    installStyles();

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", installResearchOverlay);
    } else {
        installResearchOverlay();
    }
})();

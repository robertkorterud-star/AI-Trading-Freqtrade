/* ATLAS Market Terminal compatibility fixes. */
(function () {
    "use strict";

    const originalFetch = window.fetch.bind(window);

    function normalizeBinanceSymbol(symbol) {
        const value = String(symbol || "").trim().toUpperCase();

        // Market search can expose Yahoo-style crypto symbols such as
        // SOL-USD. Binance spot candles use SOLUSDT.
        if (/^[A-Z0-9]+-USD$/.test(value)) {
            return value.slice(0, -4) + "USDT";
        }

        if (/^[A-Z0-9]+\/USD$/.test(value)) {
            return value.slice(0, -4) + "USDT";
        }

        if (/^[A-Z0-9]+USD$/.test(value)) {
            return value + "T";
        }

        return value;
    }

    window.fetch = function (input, init) {
        try {
            const rawUrl =
                typeof input === "string"
                    ? input
                    : input && input.url;

            if (rawUrl && rawUrl.includes("/api/binance-candles")) {
                const url = new URL(rawUrl, window.location.origin);
                const symbol = url.searchParams.get("symbol");
                const normalized = normalizeBinanceSymbol(symbol);

                if (normalized && normalized !== symbol) {
                    url.searchParams.set("symbol", normalized);

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
            // Fall through to normal fetch.
        }

        return originalFetch(input, init);
    };
})();

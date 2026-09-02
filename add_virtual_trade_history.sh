#!/bin/bash
set -euo pipefail

python - <<'PY'
from pathlib import Path

run_script = Path("run_atlas_dry_run.sh")
index_file = Path("atlas/dashboard/templates/index.html")
gitignore = Path(".gitignore")

run_text = run_script.read_text()

old_imports = '''from atlas.adapters.binance import BinanceAdapter\nfrom atlas.trading.dry_run_loop import DryRunLoop\nfrom atlas.agents import (\n'''
new_imports = '''import json\nfrom datetime import datetime, timezone\nfrom pathlib import Path\n\nfrom atlas.adapters.binance import BinanceAdapter\nfrom atlas.trading.dry_run_loop import DryRunLoop\nfrom atlas.agents import (\n'''
if old_imports not in run_text:
    raise SystemExit("run_atlas_dry_run.sh: import anchor not found")
run_text = run_text.replace(old_imports, new_imports, 1)

old_result = '''result = loop.process_binance(\n    adapter=adapter,\n    symbol=SYMBOL,\n    interval=INTERVAL,\n    limit=LIMIT,\n)\n\nprint("========================================")\n'''
new_result = '''result = loop.process_binance(\n    adapter=adapter,\n    symbol=SYMBOL,\n    interval=INTERVAL,\n    limit=LIMIT,\n)\n\n# Persist only actual virtual position changes.\n# This file is runtime data and is deliberately not committed.\naction_value = getattr(result.execution.action, "value", result.execution.action)\nif result.execution.executed and result.execution.quantity > 0.0:\n    action_map = {\n        "ENTER": "BUY",\n        "REDUCE": "SELL",\n        "EXIT": "SELL",\n    }\n    marker_action = action_map.get(str(action_value))\n    if marker_action:\n        history_path = Path("atlas/dashboard/static/virtual_trades.json")\n        history_path.parent.mkdir(parents=True, exist_ok=True)\n        try:\n            history = json.loads(history_path.read_text())\n            if not isinstance(history, list):\n                history = []\n        except (FileNotFoundError, json.JSONDecodeError):\n            history = []\n\n        now = datetime.now(timezone.utc)\n        event = {\n            "id": now.isoformat() + f"::{result.symbol}::{marker_action}",\n            "timestamp": int(now.replace(second=0, microsecond=0).timestamp()),\n            "timestamp_iso": now.isoformat(),\n            "symbol": result.symbol,\n            "action": marker_action,\n            "position_action": str(action_value),\n            "quantity": result.execution.quantity,\n            "price": result.execution.price,\n            "confidence": result.decision.confidence,\n            "risk_score": result.decision.risk_score,\n            "realized_pnl": result.execution.realized_pnl,\n            "equity": result.execution.equity,\n            "reason": result.execution.reason,\n        }\n\n        if not any(item.get("id") == event["id"] for item in history):\n            history.append(event)\n            history = history[-500:]\n            history_path.write_text(json.dumps(history, indent=2) + "\\n")\n            print(f"Virtual trade persisted: {marker_action} {result.symbol}")\n\nprint("========================================")\n'''
if old_result not in run_text:
    raise SystemExit("run_atlas_dry_run.sh: result anchor not found")
run_text = run_text.replace(old_result, new_result, 1)
run_script.write_text(run_text)

index_text = index_file.read_text()
old_markers = '''            // The dashboard decision is the current ATLAS signal. It is deliberately\n            // shown on the latest candle only; historical trade markers require a\n            // persisted virtual-trade event stream and are not fabricated here.\n            try {\n                const dash = await fetch('/api/dashboard?symbol=BTCUSDT', { cache: 'no-store' });\n                const snapshot = await dash.json();\n                const action = snapshot && snapshot.decision ? snapshot.decision.action : 'HOLD';\n                updateSignal(action);\n\n                if (markers && markers.detach) markers.detach();\n                if (typeof LightweightCharts.createSeriesMarkers === 'function') {\n                    markers = LightweightCharts.createSeriesMarkers(series, [{\n                        time: last.time,\n                        position: action === 'SELL' ? 'aboveBar' : 'belowBar',\n                        color: action === 'BUY' ? '#16c784' : action === 'SELL' ? '#ea3943' : '#f5a623',\n                        shape: action === 'BUY' ? 'arrowUp' : action === 'SELL' ? 'arrowDown' : 'circle',\n                        text: 'ATLAS ' + action\n                    }]);\n                }\n            } catch (e) {\n                updateSignal('HOLD');\n            }\n'''
new_markers = '''            // Render only persisted virtual executions as historical markers.\n            // No historical BUY/SELL signals are inferred from candles.\n            async function loadVirtualTradeMarkers() {\n                try {\n                    const response = await fetch('/static/virtual_trades.json?ts=' + Date.now(), { cache: 'no-store' });\n                    if (!response.ok) return [];\n                    const events = await response.json();\n                    if (!Array.isArray(events)) return [];\n\n                    const candleTimes = candles.map(candle => candle.time);\n                    const firstTime = candleTimes[0];\n                    const lastTime = candleTimes[candleTimes.length - 1];\n\n                    return events\n                        .filter(event => event && event.symbol === 'BTCUSDT')\n                        .map(event => {\n                            const eventTime = Math.floor(Number(event.timestamp));\n                            if (!Number.isFinite(eventTime)) return null;\n\n                            const nearest = candleTimes.reduce((best, time) =>\n                                Math.abs(time - eventTime) < Math.abs(best - eventTime) ? time : best,\n                                candleTimes[0]\n                            );\n\n                            if (nearest < firstTime || nearest > lastTime) return null;\n\n                            const action = event.action === 'SELL' ? 'SELL' : 'BUY';\n                            return {\n                                time: nearest,\n                                position: action === 'SELL' ? 'aboveBar' : 'belowBar',\n                                color: action === 'SELL' ? '#ea3943' : '#16c784',\n                                shape: action === 'SELL' ? 'arrowDown' : 'arrowUp',\n                                text: 'VIRTUAL ' + action\n                            };\n                        })\n                        .filter(Boolean);\n                } catch (e) {\n                    return [];\n                }\n            }\n\n            try {\n                const dash = await fetch('/api/dashboard?symbol=BTCUSDT', { cache: 'no-store' });\n                const snapshot = await dash.json();\n                const action = snapshot && snapshot.decision ? snapshot.decision.action : 'HOLD';\n                updateSignal(action);\n\n                const historicalMarkers = await loadVirtualTradeMarkers();\n                const currentMarker = {\n                    time: last.time,\n                    position: action === 'SELL' ? 'aboveBar' : 'belowBar',\n                    color: action === 'BUY' ? '#16c784' : action === 'SELL' ? '#ea3943' : '#f5a623',\n                    shape: action === 'BUY' ? 'arrowUp' : action === 'SELL' ? 'arrowDown' : 'circle',\n                    text: 'ATLAS ' + action\n                };\n\n                if (markers && markers.detach) markers.detach();\n                if (typeof LightweightCharts.createSeriesMarkers === 'function') {\n                    markers = LightweightCharts.createSeriesMarkers(\n                        series,\n                        [...historicalMarkers, currentMarker]\n                    );\n                }\n            } catch (e) {\n                updateSignal('HOLD');\n            }\n'''
if old_markers not in index_text:
    raise SystemExit("index.html: marker anchor not found")
index_file.write_text(index_text.replace(old_markers, new_markers, 1))

git_text = gitignore.read_text()
ignore_line = "atlas/dashboard/static/virtual_trades.json"
if ignore_line not in git_text:
    git_text += "\n# ATLAS virtual trade history (runtime data)\n" + ignore_line + "\n"
    gitignore.write_text(git_text)

print("Virtual trade history patch applied.")
print("- run_atlas_dry_run.sh now persists actual virtual executions")
print("- Dashboard renders persisted BUY/SELL markers")
print("- runtime history is git-ignored")
PY

chmod +x run_atlas_dry_run.sh

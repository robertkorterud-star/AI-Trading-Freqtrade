from scripts import atlas_dry_run


class FakeBinance:
    def get_klines(self, **kwargs):
        return [
            [
                1710000000000 + i * 60000,
                str(100 + i * 0.2),
                str(101 + i * 0.2),
                str(99 + i * 0.2),
                str(100.5 + i * 0.2),
                "10",
            ]
            for i in range(23)
        ]


def test_runner_is_public_data_only_and_completes_one_dry_run(monkeypatch):
    monkeypatch.setattr(atlas_dry_run, "BinanceAdapter", lambda: FakeBinance())

    result = atlas_dry_run.run_dry_run(limit=23)
    summary = atlas_dry_run._summary(result)

    assert summary["mode"] == "DRY_RUN"
    assert summary["symbol"] == "BTCUSDT"
    assert summary["paper_execution"]["equity"] > 0
    assert isinstance(summary["paper_execution"]["executed"], bool)


def test_runner_supports_multiple_symbols(monkeypatch):
    monkeypatch.setattr(atlas_dry_run, "BinanceAdapter", lambda: FakeBinance())

    results = atlas_dry_run.run_dry_runs(
        ["btcusdt", "ethusdt", "SOLUSDT"],
        limit=23,
    )
    summaries = [atlas_dry_run._summary(result) for result in results]

    assert [summary["symbol"] for summary in summaries] == [
        "BTCUSDT",
        "ETHUSDT",
        "SOLUSDT",
    ]
    assert all(summary["mode"] == "DRY_RUN" for summary in summaries)
    assert all(summary["paper_execution"]["equity"] > 0 for summary in summaries)


def test_runner_rejects_empty_symbol_list():
    try:
        atlas_dry_run.run_dry_runs([])
    except ValueError as exc:
        assert str(exc) == "at least one symbol is required"
    else:
        raise AssertionError("empty symbol list was accepted")


def test_runner_rejects_invalid_limit():
    try:
        atlas_dry_run.run_dry_run(limit=0)
    except ValueError as exc:
        assert str(exc) == "limit must be greater than zero"
    else:
        raise AssertionError("invalid limit was accepted")

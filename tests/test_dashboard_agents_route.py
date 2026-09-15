from atlas.dashboard.app import app


def test_agents_page_route_is_registered():
    route = next(
        route
        for route in app.routes
        if getattr(route, "path", None) == "/agents"
    )

    assert route.methods == {"GET"}
    assert route.endpoint.__name__ == "agents_page"

from app.services.search_query import parse_natural_search


def test_parses_price_constraint_without_polluting_lexical_query() -> None:
    parsed = parse_natural_search("bike under $150")

    assert parsed.text == "bike"
    assert parsed.maximum_price_cents == 15_000
    assert parsed.free_only is False


def test_parses_free_constraint_as_a_whole_word() -> None:
    parsed = parse_natural_search("free lamp")
    freezer = parse_natural_search("mini freezer")

    assert parsed.text == "lamp"
    assert parsed.free_only is True
    assert freezer.text == "mini freezer"
    assert freezer.free_only is False


def test_blank_and_constraint_only_queries_are_valid() -> None:
    assert parse_natural_search(" ").text is None
    assert parse_natural_search("under 25").text is None
    assert parse_natural_search("under 25").maximum_price_cents == 2_500

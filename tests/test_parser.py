from expandr.parser import collect_fields, evaluate, parse


def test_plain_text():
    result = evaluate("hello world", {})
    assert result.text == "hello world"


def test_time_and_formula():
    result = evaluate("Total {= 2 * 3}", {})
    assert result.text == "Total 6"


def test_form_and_if():
    content = "{formtext: name=price; default=10}{if: price > 5}big{else}small{endif}"
    fields = collect_fields(parse(content))
    assert fields[0].name == "price"
    assert evaluate(content, {"price": "8"}).text.endswith("big")
    assert evaluate(content, {"price": "1"}).text.endswith("small")


def test_note_hides_output_keeps_form():
    content = "{note}{formtext: name=x; default=hidden}{endnote}seen {= x}"
    fields = collect_fields(parse(content))
    assert fields[0].name == "x"
    assert evaluate(content, {"x": "Z"}).text == "seen Z"


def test_cursor_index():
    result = evaluate("ab{cursor}cd", {})
    assert result.text == "abcd"
    assert result.cursor == 2

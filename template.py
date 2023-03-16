import unittest
import re
import typing


class TemplateTest(unittest.TestCase):
    def render(self, text: str, ctx: dict, expected: str, filters: dict = None):  # type: ignore
        engine = TemplateEngine()
        if filters:
            for name, fn in filters.items():
                engine.register(name, fn)
        engine.register("upper", lambda x: x.upper())
        engine.register("strip", lambda x: x.strip())
        rendered = engine.create(text).render(ctx)
        self.assertEqual(expected, rendered)

    def test_plain_text(self):
        for text in [
                'This is a simple message.',
                '<h1>This is a html message.</h1>',
                'This is a multi message\nThis is line 2 of the message'
        ]:
            self.render(text, {}, text)

    def test_expr_single(self):
        self.render('hello, {{name}}!', {"name": "Bob"}, "hello, Bob!")

    def test_expr_array_index(self):
        self.render('hello, {{names[0]}}', {
                    "names": ["guest"]}, 'hello, guest')

    def test_expr_array_name(self):
        self.render("Hello, {{names['guest']}}!",
                    {"names": {"guest": 123}},
                    "Hello, 123!")

    def test_expr_multi(self):
        self.render("Hello, {{user}} at {{year}}!",
                    {"user": "Alice", "year": 2020},
                    "Hello, Alice at 2020!")

    def test_expr_variable_missing(self):
        with self.assertRaises(NameError):
            self.render("{{name}}", {}, "")

    def test_expr_with_filter_1(self):
        self.render("Hello, {{ name | upper }}!", {
                    "name": "Bob"}, "Hello, BOB!")

    def test_expr_with_filter_2(self):
        self.render("Hello, {{ name | upper | strip }}!",
                    {"name": "   Bob   "}, "Hello, BOB!")

    def test_expr_with_addition_filter(self):
        def first(x): return x[0]
        self.render("Hello, {{ name | upper | first }}!",
                    {"name": "alice"},
                    "Hello, A!",
                    filters={"first": lambda x: x[0]})

    def test_filter_not_defined(self):
        with self.assertRaises(NameError):
            self.render("Hello, {{ name | upper | first }}!",
                        {"name": "alice"},
                        "Hello, A!")

    def test_comment(self):
        self.render("Hello, {# This is a comment. #}World!",
                    {},
                    "Hello, World!")

    def test_comment_with_expr(self):
        self.render("Hello, {# This is a comment. #}{{name}}!",
                    {"name": "Alice"},
                    "Hello, Alice!")


"""
hello, 
{% if switch %}
    {% open_msg %}
{% else %}
    {% close_msg %}
{% endif %}
!
"""


"""
{% if switch %}
    {% open_msg %}
{% else %}
    {% close_msg %}
{% endif %}
"""


class TokenizeTest(unittest.TestCase):
    def test_single_variable(self):
        tokens = tokenize('Hello, {{name}}!')
        self.assertEqual(tokens, [
            Text('Hello, '), Expr('name'), Text('!')
        ])

    def test_two_variables(self):
        tokens = tokenize("Hello, {{name}} in {{year}}   ")
        self.assertEqual(tokens, [
            Text("Hello, "),
            Expr("name"),
            Text(" in "),
            Expr("year")
        ])

    def test_parse_repr(self):
        cases = [
            ("name", "name", []),
            ("name | upper", "name", ["upper"]),
            ("name | upper | strip", "name", ["upper", "strip"]),
            ("'a string with | inside' | upper | strip",
             "'a string with | inside'", ["upper", "strip"])
        ]

        for expr, varname, filters in cases:
            parsed_varname, parsed_filters = parse_expr(expr)
            self.assertEqual(varname, parsed_varname)
            self.assertEqual(filters, parsed_filters)

    def test_comment(self):
        tokens = tokenize("Prefix {# Comment #} Suffix")
        self.assertEqual(tokens, [
            Text("Prefix "),
            Comment("Comment"),
            Text(" Suffix"),
        ])

    def test_tokenize_for_loop(self):
        tokens = tokenize("{% for row in rows %}Loop {{ row }}{% endfor %}")
        self.assertEqual(tokens, [
            For("row", "rows"),
            Text("Loop "),
            Expr("row"),
            EndFor()
        ])


OUTPUT_VAR = "_output_"


class Template:
    def __init__(self, text: str, filters: dict = None):  # type: ignore
        self._text = text
        self._code = None
        self._global_vars = {}
        if filters:
            self._global_vars.update(filters)

    def _generate_code(self):
        if not self._code:
            tokens = tokenize(self._text)
            code_lines = [x.generate_code() for x in tokens]
            source_code = '\n'.join(code_lines)
            self._code = compile(source_code, '', 'exec')
            # self._source_code = source_code

    def render(self, ctx: dict) -> str:
        self._generate_code()
        exec_ctx = (ctx or {}).copy()
        output = []
        exec_ctx[OUTPUT_VAR] = output
        exec(self._code, self._global_vars, exec_ctx)  # type: ignore
        return "".join(output)


class TemplateEngine:
    def __init__(self):
        self._filters = {}

    def register(self, name: str, filter_):
        self._filters[name] = filter_

    def create(self, source: str) -> Template:
        return Template(source, filters=self._filters)


"""
classDiagram
    Token <|-- Text
    Token <|-- Expr
    Token : +parse(text: str) -> list[Token]
"""


class Token:
    def parse(self, content: str):
        raise NotImplementedError()

    def __eq__(self, other):
        return type(self) == type(other) and repr(self) == repr(other)

    def generate_code(self) -> str:
        raise NotImplementedError()


class Text(Token):
    def __init__(self, content: str = ""):
        self._content = content

    def __repr__(self):
        return f"Text({self._content})"

    def parse(self, content: str):
        self._content = content

    def generate_code(self) -> str:
        return f"{OUTPUT_VAR}.append({repr(self._content)})"


class Expr(Token):
    # TODO
    def __init__(self, varname: str = ""):
        self._varname = varname
        self._filters = []

    def __repr__(self):
        if self._filters:
            return f"Expr({self._varname} | {' | '.join(self._filters)})"
        return f"Expr({self._varname})"

    def parse(self, content: str):
        self._varname, self._filters = parse_expr(content)

    def generate_code(self) -> str:
        result = self._varname
        for filter in self._filters[::-1]:
            result = f"{filter}({result})"
        return f"{OUTPUT_VAR}.append(str({result}))"


class Comment(Token):

    def __init__(self, content: str = ""):
        self._content = content

    def __repr__(self):
        return f"Comment({self._content})"

    def parse(self, content: str):
        self._content = content

    def generate_code(self) -> str:
        return ""


class For(Token):
    pass


class EndFor(Token):
    pass


def tokenize(text: str) -> typing.List[Token]:
    segments = re.split(r"({{.*?}}|{#.*?#}|{%.*?%})", text)
    return [create_token(s) for s in segments if s.strip()]


def create_control_token(content: str) -> Token:
    content = content.strip()
    m = re.match(r"^(\w+)", content)
    if not m:
        raise SyntaxError(f'Unknown control token: {content}')

    keyword = m.group(1)
    token_types = {
        'for': For,
        'endfor': EndFor,
    }

    if keyword not in token_types:
        raise SyntaxError(f'Unknown control token: {content}')

    return token_types[keyword]()


def create_token(text: str) -> Token:
    """ Create and parse token from text. """
    if text.startswith("{{") and text.endswith("}}"):
        token, content = Expr(), text[2:-2].strip()
    elif text.startswith("{#") and text.endswith("#}"):
        token, content = Comment(), text[2:-2].strip()
    elif text.startswith("{%") and text.endswith("%}"):
        content = text[2:-2].strip()
        token = create_control_token(content)
    else:
        token, content = Text(), text
    token.parse(content)
    return token


def extract_last_filter(text: str) -> typing.Tuple[str, str]:
    """
    Extract last filter from expression like 'var | ... | filter'.
    return (text, None) when no more filters found.
    """
    m = re.search(r'(\|\s*[A-Za-z0-9_]+\s*)$', text)
    if m:
        suffix = m.group(1)
        filter_ = suffix[1:].strip()
        var_name = text[:-len(suffix)].strip()
        return var_name, filter_
    return text, ""


def parse_expr(text: str) -> typing.Tuple[str, typing.List[str]]:
    var_name, filters = text, []
    while True:
        var_name, filter_ = extract_last_filter(var_name)
        if filter_:
            filters.insert(0, filter_)
        else:
            break
    return var_name, filters


if __name__ == '__main__':
    unittest.main()

from ast import Expr
import unittest


from template import EndFor, For, TemplateEngine, Text, parse_expr, tokenize, Comment


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

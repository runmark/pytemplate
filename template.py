import unittest
import re
import typing


class TemplateTest(unittest.TestCase):
    def render(self, text: str, ctx: dict, expected: str):
        rendered = Template(text).render(ctx)
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

    def test_expr_variable_missing(self):
        with self.assertRaises(NameError):
            self.render("{{name}}", {}, "")

    def test_parse_repr(self):
        pass


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


OUTPUT_VAR = "_output_"


class Template:
    def __init__(self, text: str):
        self._text = text
        self._code = None

    def _generate_code(self):
        if not self._code:
            tokens = tokenize(self._text)
            code_lines = [x.generate_code() for x in tokens]
            source_code = '\n'.join(code_lines)
            self._code = compile(source_code, '', 'exec')

    def render(self, ctx: dict) -> str:
        self._generate_code()
        exec_ctx = (ctx or {}).copy()
        output = []
        exec_ctx[OUTPUT_VAR] = output
        exec(self._code, None, exec_ctx)  # type: ignore
        return "".join(output)


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

    def parse(self, content: str):
        self._content = content

    def __repr__(self):
        return f"Text({self._content})"

    def generate_code(self) -> str:
        return f"{OUTPUT_VAR}.append({repr(self._content)})"


class Expr(Token):
    def __init__(self, content: str = ""):
        self._varname = content

    def parse(self, content: str):
        self._varname = content

    def __repr__(self):
        return f"Expr({self._varname})"

    def generate_code(self) -> str:
        return f"{OUTPUT_VAR}.append(str({self._varname}))"


def tokenize(text: str) -> typing.List[Token]:
    segments = re.split(r"({{.*?}})", text)
    return [create_tokens(s) for s in segments if s.strip()]


def create_tokens(text: str) -> Token:
    if text.startswith("{{") and text.endswith("}}"):
        token, content = Expr(), text[2:-2].strip()
    else:
        token, content = Text(), text
    token.parse(content)
    return token


if __name__ == '__main__':
    unittest.main()

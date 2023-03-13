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

    # def test_variable(self):
    #     self.render('Hello, {{name}}!', {'name': 'Bob'}, 'Hello, Bob!')


class TokenizeTest(unittest.TestCase):
    def test_single_variable(self):
        tokens = tokenize('Hello, {{name}}!')
        self.assertEqual(tokens, [
            Text('Hello, '), Expr('name'), Text('!')
        ])


class Template:
    def __init__(self, text: str):
        self.text = text

    def render(self, ctx: dict) -> str:
        return self.text


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


class Text(Token):
    def __init__(self, content: str = ""):
        self._content = content

    def parse(self, content: str):
        self._content = content

    def __repr__(self):
        return f"Text({self._content})"


class Expr(Token):
    def __init__(self, content: str = ""):
        self._varname = content

    def parse(self, content: str):
        self._varname = content

    def __repr__(self):
        return f"Expr({self._varname})"


def tokenize(text: str) -> typing.List[Token]:
    segments = re.split(r"({{.*?}})", text)
    return [create_tokens(s) for s in segments]


def create_tokens(text: str) -> Token:
    if text.startswith("{{") and text.endswith("}}"):
        token, content = Expr(), text[2:-2].strip()
    else:
        token, content = Text(), text
    token.parse(content)
    return token


if __name__ == '__main__':
    unittest.main()

import unittest


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


class Template:
    def __init__(self, text: str):
        self.text = text

    def render(self, ctx: dict) -> str:
        return self.text


if __name__ == '__main__':
    unittest.main()

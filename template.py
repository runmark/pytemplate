import re
import typing

from typing import Optional


OUTPUT_VAR = "_output_"
INDENT = 1
UNINDENT = -1
INDENT_SPACES = 2
INDEX_VAR = "index"


class LoopVar:
    def __init__(self, index: int):
        self.index = index
        self.index0 = index
        self.index1 = index + 1


class CodeBuilder:
    """
    Manage code generating context GLOBALLY. 
    """

    def __init__(self):
        self.codes = []
        self._block_stack = []

    def add_control_code(self, code_line: str):
        self.codes.append(code_line)

    def add_expr(self, expr: str):
        code_line = f'{OUTPUT_VAR}.append(str({expr}))'
        # code_line = f'{OUTPUT_VAR}.append({str({expr})})'
        self.codes.append(code_line)

    def add_text(self, text: str):
        code_line = f"{OUTPUT_VAR}.append({repr(text)})"
        self.codes.append(code_line)

    def indent(self):
        self.codes.append(INDENT)

    def unindent(self):
        self.codes.append(UNINDENT)

    def code_lines(self):
        indent = 0
        for code in self.codes:
            if isinstance(code, str):
                line = ' ' * indent * INDENT_SPACES + code
                yield line
            elif code in (INDENT, UNINDENT):
                indent += code

    def source(self) -> str:
        return "\n".join(self.code_lines())

    def check_code(self):
        if self._block_stack:
            last_control = self._block_stack.pop(-1)
            raise SyntaxError(f"{last_control.name} has no end tag")

    def push_control(self, ctrl):
        self._block_stack.append(ctrl)

    def end_block(self, begin_token_type):
        block_name = begin_token_type.name
        if not self._block_stack:
            raise SyntaxError(
                f'End of block {block_name} does not found matching start tag')
        top_block = self._block_stack.pop(-1)
        if type(top_block) != begin_token_type:
            raise SyntaxError(
                f'Expected end of {block_name} block, got {top_block.name}')
        return top_block


class Template:
    def __init__(self, text: str, filters: Optional[dict] = None):
        self._text = text
        self._source = None  # source code
        self._code = None    # copiled code
        self._global_vars = {}
        if filters:
            self._global_vars.update(filters)

    def _generate_code(self):
        if not self._code:
            tokens = tokenize(self._text)
            builder = CodeBuilder()
            for token in tokens:
                token.generate_code(builder)
            builder.check_code()
            self._source = builder.source()
            self._code = compile(self._source, '', 'exec')
            # self._source_code = source_code

    def render(self, ctx: dict) -> str:
        self._generate_code()
        exec_ctx = (ctx or {}).copy()
        output = []
        exec_ctx.update({
            OUTPUT_VAR: output,
            'LoopVar': LoopVar,
        })
        exec(self._code, self._global_vars, exec_ctx)  # type: ignore
        return "".join(output)


class TemplateEngine:
    def __init__(self):
        self._filters = {}

    def register_filter(self, name: str, filter_):
        self._filters[name] = filter_

    def register_default_filters(self):
        self.register_filter('upper', lambda x: x.upper())
        self.register_filter('strip', lambda x: x.strip())

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

    def generate_code(self, builder: CodeBuilder):
        """
        code str append directly, text str append with quote. 
        """
        raise NotImplementedError()


class Text(Token):
    def __init__(self, content: str = ""):
        self._content = content

    def __repr__(self):
        return f"Text({self._content})"

    def parse(self, content: str):
        self._content = content

    def generate_code(self, builder: CodeBuilder):
        builder.add_text(self._content)
        # return f"{OUTPUT_VAR}.append({repr(self._content)})"


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

    def generate_code(self, builder: CodeBuilder):
        result = self._varname
        for filter in self._filters[::-1]:
            result = f"{filter}({result})"
        builder.add_expr(result)
        # return f"{OUTPUT_VAR}.append(str({result}))"


class Comment(Token):

    def __init__(self, content: str = ""):
        self._content = content

    def __repr__(self):
        return f"Comment({self._content})"

    def parse(self, content: str):
        self._content = content

    def generate_code(self, builder: CodeBuilder):
        pass


class For(Token):
    name = 'for'

    def __init__(self, var_name: Optional[str] = None, target: Optional[str] = None):
        self._var_name = var_name
        self._target = target

    def __repr__(self):
        return f'For({self._var_name} in {self._target})'

    def parse(self, content: str):
        m = re.match(r'for\s+(\w+)\s+in\s+(\w+)', content)
        if not m:
            raise SyntaxError(f'Invalid for block: {content}')
        self._var_name = m.group(1)
        self._target = m.group(2)

    def generate_code(self, builder: CodeBuilder):
        builder.add_control_code(
            f"for {INDEX_VAR}, {self._var_name} in enumerate({self._target}):")
        builder.indent()
        builder.push_control(self)
        builder.add_control_code(f"loop = LoopVar({INDEX_VAR})")


class EndFor(Token):
    def parse(self, content: str):
        pass

    def generate_code(self, builder: CodeBuilder):
        builder.unindent()
        builder.end_block(For)

    def __repr__(self):
        return "repr"


def tokenize(text: str) -> typing.List[Token]:
    segments = re.split(r"({{.*?}}|{#.*?#}|{%.*?%})", text)
    return [create_token(s) for s in segments if s.strip()]


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

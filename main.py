from random import randint
import re
from contextlib import suppress, contextmanager
from pprint import pprint
from collections.abc import Iterable

file_name = 'code.cpp'

with open('code.cpp', 'r') as file:
    code = file.read()


def rand_chance(how_many, from_amount):
    return randint(1, from_amount) < how_many


def throw_coin():
    return rand_chance(1, 2)


class RefSetting:
    indent = 4


class StrIterator:
    def __init__(self, text, index):
        self.text = text
        self.index = index

    def shift(self, value):
        self.index += value

    def copy(self):
        return StrIterator(self.text, self.index)

    def fill_from(self, other):
        self.index = other.index

    @property
    def string(self):
        if self.index >= len(self.text):
            print('OUT OF RANGE')
            raise NotFitException
        return self.text[self.index:]

    def is_end(self):
        return self.index >= len(self.text)


class NotFitException(Exception):
    pass


def merge(*items):
    res = []
    for item in items:
        if isinstance(item, str):
            res.append(item)
        elif isinstance(item, CodePart):
            res.append(item.refactor())
        elif isinstance(item, Iterable):
            res.append(merge(*item))
        else:
            raise TypeError(item)

    return ''.join(res)


def refactor_list(items, prefix='', **kwargs):
    def adjust_value(value):
        return prefix + value

    return list(
        map(
            lambda x: adjust_value(x.refactor(**kwargs)) if isinstance(x, CodePart) else adjust_value(x), items
        )
    )


def add_word(need_add, word, prefix=False, postfix=False):
    if not need_add:
        return ''

    return word


def suppress_spaces(it):
    with suppress(NotFitException):
        fit(it, CSpaces, pass_spaces=False)


def fit_regex(it, regex):
    match = re.match(regex, it.string)
    if not match:
        raise NotFitException
    value = match.group(0)
    assert isinstance(value, str)
    it.shift(len(value))
    return value


def fit(it, template, block_it=False, allow_spaces=True, sep=None, pass_spaces=True):
    if block_it:
        it = it.copy()
    if pass_spaces:
        suppress_spaces(it)

    if type(template) is type and issubclass(template, CodePart):
        return template.fit(it)

    elif isinstance(template, str):
        return fit_regex(it, template)

    elif isinstance(template, list):
        temp = template[0]
        items = [fit(it, temp)]
        while True:
            next_item = None
            with try_fit(it) as f:
                if allow_spaces:
                    suppress_spaces(it)

                if sep:
                    f(sep)
                    if allow_spaces:
                        suppress_spaces(it)
                next_item = [f(temp)]

            if not next_item:
                break
            items += next_item

        return items
    else:
        raise TypeError(template)


def have_item(it, item):
    with try_fit(it) as f:
        f(item)
    return f.success


@contextmanager
def try_fit(it):
    it_copy = it.copy()

    def safe_fit(*args, **kwargs):
        return fit(it_copy, *args, **kwargs)

    safe_fit.success = True

    try:
        yield safe_fit
    except NotFitException:
        safe_fit.success = False
        pass
    else:
        it.fill_from(it_copy)


def specific_symbol(symbol):
    class SpecificSymbol(CSymbol):
        @classmethod
        def fit(cls, it):
            parse_res = CSymbol.fit(it)
            if parse_res and parse_res.symbol != symbol:
                raise NotFitException
            return parse_res

    return SpecificSymbol


def specific_word(word):
    class SpecificWord(CWord):
        @classmethod
        def fit(cls, it):
            parse_res = CWord.fit(it)
            if parse_res and parse_res.word != word:
                raise NotFitException
            return parse_res

    return SpecificWord


class CodePart:

    def __init__(self, *items):
        self.items = items

    @classmethod
    def parse(cls, it):
        try:
            it_copy = it.copy()
            res = cls.fit(it_copy)
            if res is None:
                raise NotFitException
            it.fill_from(it_copy)
            return res
        except NotFitException:
            return None

    def refactor(self, **kwargs):
        return merge(self.items)

    @classmethod
    def fit(cls, it):
        raise NotImplementedError

    def __repr__(self):
        rep = self.refactor().replace('    ', ' ')
        n = '\n'
        return f'{self.__class__.__name__}({rep.replace(n, " ")[:100]})'


class CSpaces(CodePart):
    @classmethod
    def fit(cls, it):
        return cls(fit_regex(it, r'\s+'))


class CSymbol(CodePart):
    def __init__(self, symbol):
        self.symbol = symbol
        super().__init__(symbol)

    @classmethod
    def fit(cls, it):
        return cls(fit_regex(it, '.|\n'))


class CSemicolon(CodePart):
    @classmethod
    def fit(cls, it):
        return cls(fit_regex(it, ';'))


class CComma(CodePart):
    @classmethod
    def fit(cls, it):
        return cls(fit_regex(it, ','))


class CWord(CodePart):
    def __init__(self, items):
        self.word = items
        super().__init__(items)

    @classmethod
    def fit(cls, it):
        return cls(fit_regex(it, r'[a-zA-Z_]\w*'))


class CInclude(CodePart):
    def __init__(self, name, value, det1, det2):
        self.name = name
        self.value = value
        self.det1 = det1
        self.det2 = det2

    @classmethod
    def fit(cls, it):
        fit(it, specific_symbol('#'))
        name = fit(it, specific_word('include'), allow_spaces=False)
        suppress_spaces(it)
        det = ''
        with try_fit(it) as f:
            det = f(specific_symbol('<'))
        if not det:
            det = fit(it, specific_symbol('"'))
        suppress_spaces(it)
        value = fit(it, CWord)
        det2 = fit(it, CSymbol)
        return cls(name, value, det, det2)

    def refactor(self, **kwargs):
        return f'#{self.name.refactor(**kwargs)} {self.det1.refactor(**kwargs)}{self.value.refactor(**kwargs)}{self.det2.refactor(**kwargs)}'


class CColon2(CodePart):
    @classmethod
    def fit(cls, it):
        return cls(fit_regex(it, '::'))


class CWordsList(CodePart):
    @classmethod
    def fit(cls, it):
        items = fit(it, [CWord], sep=CComma)
        return cls(items)

    def refactor(self, **kwargs):
        return merge(', '.join(refactor_list(self.items)))


class CTypeFull(CodePart):
    def __init__(self, c_type, const, link, pointer):
        self.type = c_type
        self.const = const
        self.link = link
        self.pointer = pointer

    @classmethod
    def fit(cls, it):
        const = have_item(it, specific_word('const'))
        c_type = fit(it, CType)
        const |= have_item(it, specific_word('const'))
        link = have_item(it, specific_symbol('&'))
        pointer = have_item(it, specific_symbol('*'))
        return cls(c_type, const, link, pointer)

    def refactor(self, **kwargs):
        res = ''
        res += add_word(self.const, 'const ')
        res += self.type.refactor(**kwargs)
        res += add_word(self.link, ' & ')
        res += add_word(self.pointer, ' * ')
        return res


class CType(CodePart):
    def __init__(self, name, args, namespace):
        assert isinstance(name, CWord)
        assert isinstance(args, list)
        self.name = name
        self.args = args
        self.namespace = namespace

    @classmethod
    def fit(cls, it):
        with try_fit(it) as f:
            namespace = f(CWord)
            f(CColon2)
        if not f.success:
            namespace = None

        with try_fit(it) as f:
            type_name = f(CWord)
            f(specific_symbol('<'))
            args = f([CType], sep=CComma)
            f(specific_symbol('>'))
            return cls(type_name, args, namespace)

        return cls(fit(it, CWord), [], namespace)

    def refactor(self, **kwargs):
        res = ''
        if self.namespace:
            res += self.namespace.refactor(**kwargs) + ' :: '
        res += self.name.refactor(**kwargs)
        if self.args:
            res += f' <{", ".join(refactor_list(self.args))}>'
        return res


class CFuncArgument(CodePart):
    def __init__(self, v_type, v_name):
        self.type = v_type
        self.name = v_name

    @classmethod
    def fit(cls, it):
        var_type = fit(it, CTypeFull)
        var_name = fit(it, CWord)
        return cls(var_type, var_name)

    def refactor(self, **kwargs):
        res = ''
        res += self.type.refactor(**kwargs) + ' '
        res += self.name.refactor(**kwargs)
        return res


class CFuncArguments(CodePart):
    def __init__(self, args):
        self.args = args

    @classmethod
    def fit(cls, it):
        fit(it, specific_symbol('('))
        args = []
        with try_fit(it) as f:
            args = f([CFuncArgument], sep=CComma)
        fit(it, specific_symbol(')'))

        return cls(args)

    def refactor(self, **kwargs):
        return f"({', '.join(refactor_list(self.args))})"


class CFuncFullName(CodePart):
    def __init__(self, name, virtual, friend, const):
        self.name = name
        self.virtual = virtual
        self.friend = friend
        self.const = const

    @classmethod
    def fit(cls, it):
        virtual = have_item(it, specific_word('virtual'))
        friend = have_item(it, specific_word('friend'))

        name = None
        with try_fit(it) as f:
            name = f(CMethodDestructor)
        if not name:
            with try_fit(it) as f: name = f(CMethodConstructor)
        if not name:
            with try_fit(it) as f: name = f(CFuncName)
        if not name:
            raise NotFitException

        const = have_item(it, specific_word('const'))
        return cls(name, virtual, friend, const)

    def refactor(self, **kwargs):
        res = ''
        if self.virtual: res += 'virtual '
        if self.friend: res += 'friend '

        res += self.name.refactor(**kwargs)

        if self.const: res += ' const'

        return res


class CFuncNameString(CodePart):
    def __init__(self, word, operation):
        self.word = word
        self.operation = operation

    @classmethod
    def fit(cls, it):
        operation = None
        word = None
        with try_fit(it) as f:
            f(specific_word('operator'))
            operation = f(r'[^(]+')
        if not f.success:
            word = fit(it, CWord)
        return cls(word, operation)

    def refactor(self, **kwargs):
        if self.word:
            return self.word.refactor(**kwargs)
        return f'operator {self.operation}'


class CFuncName(CodePart):
    def __init__(self, c_type, c_class, c_name, c_args):
        self.c_type = c_type
        self.c_class = c_class
        self.c_name = c_name
        self.c_args = c_args

    @classmethod
    def fit(cls, it):

        c_type = fit(it, CTypeFull)
        with try_fit(it) as f:
            c_class = f(CWord)
            f(CColon2)

        if not f.success:
            c_class = None

        c_name = fit(it, CFuncNameString)
        c_args = fit(it, CFuncArguments)

        return cls(c_type, c_class, c_name, c_args)

    def refactor(self, **kwargs):
        if self.c_class:
            return '{} {}::{} {}'.format(*refactor_list([self.c_type, self.c_class, self.c_name, self.c_args]))
        else:
            return '{} {} {}'.format(*refactor_list([self.c_type, self.c_name, self.c_args]))


class CFuncDeclaration(CodePart):
    def __init__(self, func):
        self.func = func

    @classmethod
    def fit(cls, it):
        func = fit(it, CFuncFullName)
        fit(it, CSemicolon)
        return cls(func)

    def refactor(self, **kwargs):
        return f'{self.func.refactor(**kwargs)};'


class CBody(CodePart):
    def __init__(self, expressions):
        self.expressions = expressions

    @classmethod
    def fit(cls, it):
        fit(it, specific_symbol('{'))
        expressions = []
        with try_fit(it) as f:
            expressions = f([CCommand])
        fit(it, specific_symbol('}'))
        return cls(expressions)

    def refactor(self, indent=0, **kwargs):
        content_indent = indent + RefSetting.indent
        prefix = '\n' + ' ' * content_indent
        bracket_indent = ' ' * indent
        return '{' + \
               ''.join(refactor_list(self.expressions, prefix=prefix, indent=content_indent)) + \
               '\n' + bracket_indent + '}'


class CBodyOrInstruction(CodePart):
    def __init__(self, body, exp):
        self.body = body
        self.exp = exp

    @classmethod
    def fit(cls, it):
        body = None
        with try_fit(it) as f:
            body = f(CBody)

        exp = None
        if not f.success:
            exp = fit(it, CCommand)

        return cls(body, exp)

    def refactor(self, **kwargs):
        if self.body:
            return self.body.refactor(**kwargs)

        return self.exp.refactor(**kwargs)


class CConstructionIfElse(CodePart):
    def __init__(self, exp, body, else_body):
        self.exp = exp
        self.body = body
        self.else_body = else_body

    @classmethod
    def fit(cls, it):
        fit(it, specific_word('if'))
        exp = fit(it, CExpressionInBrackets)
        body = fit(it, CBodyOrInstruction)
        else_body = None
        with try_fit(it) as f:
            f(specific_word('else'))
            else_body = f(CBodyOrInstruction)
        return cls(exp, body, else_body)

    def refactor(self, **kwargs):
        res = f'if {self.exp.refactor(**kwargs)} {self.body.refactor(**kwargs)}'
        if self.else_body:
            res += f' else {self.else_body.refactor(**kwargs)}'
        return res


class CExpressionUntilBracket(CodePart):
    @classmethod
    def fit(cls, it):
        s = fit_regex(it, r'[^)]+')
        while s.count('(') != s.count(')'):
            s += ')'
            it.shift(1)
            s += fit_regex(it, r'[^)]*')

        return cls(s)


class CExpressionInBrackets(CodePart):
    def __init__(self, exp):
        self.exp = exp

    @classmethod
    def fit(cls, it):
        fit(it, specific_symbol('('))
        exp = CEmpty()
        with try_fit(it) as f:
            exp = f(CExpressionUntilBracket)

        fit(it, specific_symbol(')'))
        return cls(exp)

    def refactor(self, **kwargs):
        return f'( {self.exp.refactor(**kwargs)} )'


class CFullExpression(CodePart):
    @classmethod
    def fit(cls, it):
        with try_fit(it) as f:
            f(specific_symbol('}'))
        if f.success:
            raise NotFitException
        return cls(fit(it, r'[^;]*;'))


class CCommand(CodePart):
    @classmethod
    def fit(cls, it):
        with try_fit(it) as f: return cls(f(CConstructionIfElse))
        with try_fit(it) as f: return cls(f(CConstructionFor))
        with try_fit(it) as f: return cls(f(CFullExpression))
        raise NotFitException


class CFuncImplementation(CodePart):
    def __init__(self, name, body):
        self.name = name
        self.body = body

    @classmethod
    def fit(cls, it):
        name = fit(it, CFuncFullName)
        body = fit(it, CBody)
        return cls(name, body)

    def refactor(self, **kwargs):
        return f'{self.name.refactor(**kwargs)} {self.body.refactor(**kwargs)}'


class CMethodDestructor(CodePart):
    @classmethod
    def fit(cls, it):
        return cls(fit(it, specific_symbol('~')), fit(it, CMethodConstructor))


class CEmpty(CodePart):
    @classmethod
    def fit(cls, it):
        raise NotFitException

    def refactor(self, **kwargs):
        return ''


class CMethodConstructor(CodePart):
    def __init__(self, name, args):
        self.name = name
        self.args = args

    @classmethod
    def fit(cls, it):
        name = fit(it, CWord)
        args = fit(it, CFuncArguments)
        return cls(name, args)

    def refactor(self, **kwargs):
        return f'{self.name.refactor(**kwargs)} {self.args.refactor(**kwargs)}'


class CConstructionFor(CodePart):
    def __init__(self, e1, e2, e3, body):
        self.e1 = e1
        self.e2 = e2
        self.e3 = e3
        self.body = body

    @classmethod
    def fit(cls, it):
        fit(it, specific_word('for'))
        fit(it, specific_symbol('('))
        e1 = fit(it, CFullExpression)
        e2 = fit(it, CFullExpression)
        e3 = CEmpty()
        with try_fit(it) as f:
            e3 = f(CExpressionUntilBracket)

        fit(it, specific_symbol(')'))
        body = fit(it, CBodyOrInstruction)
        return cls(e1, e2, e3, body)

    def refactor(self, **kwargs):
        return f'for ({self.e1.refactor()} {self.e2.refactor()} {self.e3.refactor()}) {self.body.refactor(**kwargs)}'


class CFunc(CodePart):
    @classmethod
    def fit(cls, it):
        with try_fit(it) as f: return f(CFuncDeclaration)
        return f(CFuncImplementation)


# class CClass(CodePart):
#     @classmethod
#     def fit(cls, it):
#         fit(it, specific_word('class'))
#         fit(it, specific_symbol('{'))
#         fit(it, [CFunc])
#         fit(it, specific_symbol('}'))


c_elements = [
    CSpaces,
    CInclude,
    CFuncDeclaration,
    CFuncImplementation,
    CCommand,
    CWord,
    CSymbol
]

if __name__ == '__main__':
    code_elements = []
    iterator = StrIterator(code, 0)
    while not iterator.is_end():
        for CPart in c_elements:
            c_part = CPart.parse(iterator)
            if c_part:
                code_elements.append(c_part)
                break

    pprint(code_elements)
    refactored_code = ''.join(map(lambda x: x.refactor(), code_elements))
    refactored_code_name = f'[{file_name.split(".")[0]}]refactored.{file_name.split(".")[-1]}'
    with open(refactored_code_name, 'w') as file:
        file.write(refactored_code)

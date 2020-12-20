import re
from collections import Iterable
from contextlib import suppress, contextmanager

from exceptions import NotFitException


class CodePart:
    @classmethod
    def parse(cls, it):
        try:
            it_copy = it.copy()
            res = cls(it_copy)
            it.fill_from(it_copy)
            return res
        except NotFitException:
            return None

    def refactor(self, **kwargs):
        return merge(self.value, **kwargs)

    def __repr__(self):
        rep = self.refactor().replace('    ', ' ')
        n = '\n'
        return f'{self.__class__.__name__}({rep.replace(n, " ")[:100]})'

    def __str__(self):
        return self.refactor()


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


def merge(*items, **kwargs):
    res = []
    prefix = ''
    for item in items:
        if isinstance(item, str):
            res.append(prefix + item)
        elif isinstance(item, CodePart):
            res.append(item.refactor(**kwargs))
        elif isinstance(item, Iterable):
            res.append(merge(*item, **kwargs))
        else:
            raise TypeError(item)

    return ''.join(res)


@contextmanager
def try_fit(it):
    it_copy = it.copy()

    def safe_fit(*args, **kwargs):
        return fit(it_copy, *args, **kwargs)

    safe_fit.success = True
    safe_fit.fail = False

    try:
        yield safe_fit
    except NotFitException:
        safe_fit.success = False
        safe_fit.fail = True
        pass
    else:
        it.fill_from(it_copy)


def refactor_list(items, prefix='', join=None, **kwargs):
    def adjust_value(value):
        return merge(value, **kwargs)

    res = list(
        map(
            lambda x: adjust_value(x.refactor(**kwargs)) if isinstance(x, CodePart) else adjust_value(x), items
        )
    )
    if join:
        res = join.join(res)
    return res


def add_word(need_add, word):
    if not need_add:
        return ''

    return word


def suppress_spaces(it):
    with suppress(NotFitException):
        from lang_objects import CSpaces
        fit(it, CSpaces, pass_spaces=False)


def have_item(it, item):
    with try_fit(it) as f:
        f(item)
    return f.success


def fit_choice(it, *templates):
    for temp in templates:
        with try_fit(it) as f:
            return f(temp)

    raise NotFitException


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
        return template(it)

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

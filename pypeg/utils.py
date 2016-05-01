import pypeg.core
from itertools import cycle


__author__ = 'Jan Růžička'
__email__ = 'jan.ruzicka01@gmail.com'

__version__ = '0.1'


# Classes to help the parser.

class ParseError(Exception):
    pass


# Functions used to process AST.

def r_zip(a, b):
    if len(a) > len(b):
        i, c = a, cycle(b)

    elif len(b) < len(a):
        i, c = b, cycle(a)

    else:
        return list(zip(a, b))

    out = []

    for x in i:
        out.append((x, next(c)))

    return out


def cut_off(a, string, **kw):
    l = list(map(len, a))

    for x in l:
        string = replace_ignored(string, **kw)[x:]

    return string


def replace_ignored(string, **kw):
    ig = kw.get('ignore', None)
    sep = kw.get('sep', None)

    if ig is not None and type(ig) is str:
        ig = pypeg.core.s(ig)

    if sep is not None and type(sep) is str:
        sep = pypeg.core.s(sep)

    while True:
        if sep is not None and sep.test(string, not_whole=True):
            string, _ = sep.parse(string, not_whole=True)

            sep = None

        elif ig is not None and ig.test(string, not_whole=True):
            string, _ = ig.parse(string, not_whole=True)

        else:
            break

    return string


def separate(string, **kw):
    sep = kw.get('sep', None)

    if sep is not None and type(sep) is not str:
        raise TypeError('Expected str, got {}!'.format(type(sep)))

    return string.split(sep)


def check_whole(string, **kw):
    if not kw.get('not_whole', False):
        string = replace_ignored(string, **kw)

        if len(string) > 0 and not kw.get('not_whole', False):
            raise ParseError('Full string cannot be matched, this remains: "{}"'.format(string))


def static_vars(**attrs):
    def __dec__(f):
        for k, v in attrs.items():
            setattr(f, k, v)

        return f

    return __dec__


def recursive_reverse(lst):
    if type(lst) is list:
        lst = lst[::-1]

        for i, x in enumerate(lst):
            if type(x) in {list, tuple}:
                lst[i] = recursive_reverse(x)

    return lst


@static_vars(cache=[])
def associate(operand, ops, a):
    if (operand, ops, a) in associate.cache:
        return associate.cache[associate.cache.index((operand, ops, a)) + 1]

    else:
        bak = a.copy()

    for i, x in enumerate(a):
        if type(x) is list:
            if len(x) == 1:
                a[i] = x[0]

            else:
                a[i] = associate(operand, ops, x)

    # Hunt for unary operators

    for o in [x for x in ops if x[1] == 1]:
        restart = True

        while restart:
            i = 0

            restart = False

            while i < len(a):
                try:
                    o[0].parse(a[i])

                    try:
                        if type(a[i+1]) not in {list, tuple}:
                            operand.parse(a[i+1])

                    except (IndexError, ParseError):
                        i += 1

                        continue

                    for x in [x[0] for x in ops if x[1] == 2]:
                        try:
                            x.parse(a[i-1])

                            break

                        except (IndexError, ParseError):
                            continue

                    else:
                        break

                    if o[2] == 0:
                        a = a[:i] + [a[i:i+2]] + a[i+2:]

                    else:
                        a = a[:i-1] + [a[i-1:i+1]] + a[i+1:]

                    i = 0
                    continue

                except ParseError:
                    pass

                i += 1

    for o in [x for x in ops if x[1] == 2]:
        i = 0

        if o[2] == 1:  # Right associative
            a = recursive_reverse(a)

        while i < len(a):
            try:
                o[0].parse(a[i])

                a = a[:i-1] + [a[i-1:i+2]] + a[i+2:]

                i = 0
                continue

            except ParseError:
                pass

            i += 1

        if o[2] == 1:  # Right associative
            a = recursive_reverse(a)

    while len(a) == 1 and type(a[0]) is list:
        a = a[0]

    associate.cache += [(operand, ops, bak), a]

    return a


# Functions to help constructing grammar.

def singleton(cls):
    obj = cls()
    obj.__name__ = cls.__name__

    return obj

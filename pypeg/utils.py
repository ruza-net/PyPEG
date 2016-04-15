from itertools import cycle

__author__ = 'Jan Růžička'
__email__ = 'jan.ruzicka01@gmail.com'

__version__ = '0.1'


class ParseError(Exception):
    pass


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


# Utility functions


def cut_off(a, string, **kw):
    l = list(map(len, a))

    for x in l:
        string = replace_ignored(string, **kw)[x:]

    return string


def replace_ignored(string, **kw):
    ig = kw.get('ignore', None)
    sep = kw.get('sep', None)

    if ig is not None and type(ig) is not str:
        raise TypeError('Expected str, got {}!'.format(type(ig)))

    while True:
        if sep is not None and string[:len(sep)] == sep:
            string = string[len(sep):]

            sep = None

        elif ig is not None and string[:len(ig)] == ig:
            string = string[len(ig):]

        else:
            break

    return string


def separate(string, **kw):
    sep = kw.get('sep', None)

    if sep is not None and type(sep) is not str:
        raise TypeError('Expected str, got {}!'.format(type(sep)))

    return string.split(sep)


def check_whole(string, **kw):
    string = replace_ignored(string, **kw)

    if len(string) > 0 and not kw.get('not_whole', False):
        raise ParseError('Full string cannot be matched, this remains: "{}"'.format(string))


def recursive_reverse(lst):
    if type(lst) is list:
        lst = lst[::-1]

        for i, x in enumerate(lst):
            if type(x) in {list, tuple}:
                lst[i] = recursive_reverse(x)

    return lst


def associate(ops, a):
    for i, x in enumerate(a):
        if type(x) is list:
            a[i] = associate(ops, x)

    for o in ops:
        i = 0

        if o[2] == 1:  # Right associative
            a = recursive_reverse(a)

        while i < len(a):
            x = a[i]

            try:
                o[0].parse(x)

                if o[1] == 0:  # Unary operator
                    a = a[:i-1] + [a[i-1:i+1]] + a[i+1:]

                else:
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

    return a

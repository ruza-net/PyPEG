import pypeg.core


__author__ = 'Jan Růžička'
__email__ = 'jan.ruzicka01@gmail.com'

__version__ = '0.1'


# Classes to help the parser.

class ParseError(Exception):
    pass


class BlockInterrupt(Exception):
    pass


# Functions used to process AST.

def cut_off(a, string, **kw):
    l = list(map(len, a))

    for x in l:
        string = replace_ignored(string, **kw)[x:]

    return string


def split(string, delim):
    out = []

    if type(delim) is pypeg.suppress:
        raise TypeError('2nd argument `delim` can\'t be suppressed!')

    line = string

    i = 0

    while i < len(string):
        try:
            string, a = delim.parse(string[i:], not_whole=True)

            out.append(line[:len(line) - len(string) - 1 * len(a)])

            line = string
            i = 0

        except ParseError:
            i += 1

    out.append(line)

    return [x for x in out if len(x) > 0]


def trim_comments(string, comment_marker, end_comment='\n', quote_markers={'"', '\''}):
    out = ''

    quoted_by = None
    commented = False

    for c in string:
        if not commented:
            if quoted_by is None and c == comment_marker:
                commented = True

                continue

            elif c in quote_markers:
                quoted_by = c if quoted_by is None else None

            out += c

        elif c == end_comment:
            commented = False

    return out


def replace_ignored(string, **kw):
    ig = kw.get('ignore', None)

    if ig is None:
        return string

    if type(ig) is not str:
        raise TypeError('I can ignore parts of string only using RegEx!')

    ig = pypeg.core.compile(ig)

    while True:
        a = ig.match(string)

        if not a:
            return string

        string = string[len(a.group(0)):]


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


def without_el(source, target):
    if source == target:
        return []

    if hasattr(source, 'el'):
        return without_el(source.el, target)

    elif hasattr(source, 'a') and hasattr(source, 'b'):
        return without_el(source.a, target) + without_el(source.b, target)

    else:
        return [source]


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

    if len(a) < 3:
        return a

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

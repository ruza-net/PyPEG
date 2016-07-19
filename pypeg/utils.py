import pypeg.core


__author__ = 'Jan Růžička'
__email__ = 'jan.ruzicka01@gmail.com'

__version__ = '0.1'


# Classes to help the parser.

class ParseError(Exception):
    pass


class FatalParseError(Exception):
    pass


class BlockInterrupt(Exception):
    pass


# Functions to help the parser

def to_valid_element(other):
    if not isinstance(other, pypeg.ParserElement):
        if type(other) is str:
            other = pypeg.s(other)

        elif type(other) is list and len(other) == 1:
            other = pypeg.group(other[0])

        else:
            raise NotImplementedError()

    return other


# Functions used to process AST.

def trim_comments(string, comment_marker, *, end_comment='\n', quote_markers=None, nested_comments=True):
    out = ''

    quote_markers = {'"', '\''} if quote_markers is None else quote_markers

    commented = 0
    quoted_by = None

    i = 0

    while i < len(string):
        if not commented:
            if quoted_by is None and string[i:len(comment_marker) + i] == comment_marker:
                commented += 1

                i += 1

                continue

            else:
                for q in quote_markers:
                    if string[i:len(q) + i] == q:
                        if quoted_by == q:
                            quoted_by = None

                        break

            out += string[i]

        elif string[i:len(end_comment) + i] == end_comment:
            commented -= 1 if nested_comments else commented

            i += len(end_comment)

            continue

        i += 1

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
        i = 0

        while i < len(a):
            try:
                o[0].parse(a[i])

                try:
                    if type(a[i+1]) not in {list, tuple}:
                        operand.parse(a[i+1])

                except (IndexError, ParseError):
                    i += 1

                    continue

                if i > 0:
                    try:
                        if type(a[i-1]) in {list, tuple}:
                            i += 1

                            continue

                        operand.parse(a[i-1])

                        i += 1
                        continue

                    except ParseError:
                        pass

                a = a[:i] + [a[i:i+2]] + a[i+2:]

                i = 0
                continue

            except ParseError:
                pass

            i += 1

    if len(a) < 3:
        return a

    for o in [x for x in ops if x[1] == 2]:
        i = 0

        if o[2] == 2:  # No-associative - parallel operators
            j = 0

            while j < len(a):
                try:
                    o[0].parse(a[j])

                    break

                except ParseError:
                    j += 1

            else:
                continue

            i = j

            while i < len(a):
                try:
                    o[0].parse(a[i])

                    i += 2

                except ParseError:
                    break

            a[j-1:i] = [a[j-1:i]]

        else:
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

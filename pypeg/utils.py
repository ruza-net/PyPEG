import pypeg.core


__author__ = 'Jan Růžička'
__email__ = 'jan.ruzicka01@gmail.com'

__version__ = '1.0'


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
    return [recursive_reverse(x) if type(x) is list else x for x in lst[::-1]]


# Functions to help constructing grammar.

def singleton(cls):
    obj = cls()
    obj.__name__ = cls.__name__

    return obj

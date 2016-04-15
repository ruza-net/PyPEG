import sre_constants
from re import compile
from pypeg.utils import *
from itertools import count

__author__ = 'Jan Růžička'
__email__ = 'jan.ruzicka01@gmail.com'

__version__ = '0.1'


# Primitive class


class ParserElement:
    __slots__ = ['value']

    def __init__(self, value):
        if type(value) is not str:
            raise TypeError('ParserElement\'s primitive value must a string, got {} instead!'.format(type(value)))

        self.value = value

    def opt(self):
        return optional(self)

    def spr(self):
        return suppress(self)

    def __add__(self, other):
        if not isinstance(other, ParserElement):
            if type(other) is str:
                other = s(other)

            elif type(other) is list and len(other) == 1:
                other = group(other[0])

            else:
                raise NotImplementedError()

        return combinator(self, other)

    def __mod__(self, other):
        if not isinstance(other, ParserElement):
            if type(other) is str:
                other = s(other)

            elif type(other) is list and len(other) == 1:
                other = group(other[0])

            else:
                raise NotImplementedError()

        return other.spr() + self + other.spr()

    def __matmul__(self, other):
        if not hasattr(other, '__call__'):
            raise NotImplementedError()

        return debugged(self, other)

    def __floordiv__(self, other):
        if not hasattr(other, '__call__') and len([x for x in other if not hasattr(x, '__call__')]) > 1:
            raise NotImplementedError()

        return apply(self, other)

    def __or__(self, other):
        if not isinstance(other, ParserElement):
            if type(other) is str:
                other = s(other)

            elif type(other) is list and len(other) == 1:
                other = group(other[0])

            else:
                raise NotImplementedError()

        return union(self, other)

    def __eq__(self, other):
        if type(other) is str:
            return named(self, other)

        else:
            raise NotImplementedError()

    def __rshift__(self, other):
        if type(other) is str:
            return take_out(self, other)

        else:
            raise NotImplementedError()

    def __invert__(self):
        return negative(self)

    def __getitem__(self, item):
        if type(item) is not slice:
            raise NotImplementedError()

        if item.stop is not None and item.stop < item.start:
            print('Warning: Minimal count is bigger than maximal count, '
                  'just letting you know that the maximal count will be used!')

        return counter(self, item.start, item.stop)


# Specialized elements


class s(ParserElement):
    __slots__ = ['value']

    def __init__(self, value):
        super(s, self).__init__(value)

        self.value = value

    def copy(self):
        return s(self.value)

    def r(self):
        return r(self.value)

    def __str__(self):
        return 's\'' + self.value + '\''

    def parse(self, string, **kw):
        out = []

        try:
            out += s(self.value).parse_token(string)

        except ParseError:
            try:
                string = replace_ignored(string, **kw)

                out += s(self.value).parse_token(string)

            except ParseError:
                raise ParseError(
                    ('Invalid syntax at: "{}"\n' + ' ' * 23 + 'Expecting: "{}"').format(string, self.value))

        string = string[len(self.value):]

        check_whole(string, **kw)

        return string, out

    def parse_token(self, string):
        i = 1

        while i <= len(string):
            try:
                if self.value != string[:i]:
                    raise ParseError('Invalid syntax: "{}"'.format(string[:i]))

                return [self.value]

            except ParseError:
                i += 1

        raise ParseError('Can\'t parse a single token from: "{}"'.format(string))


class r(ParserElement):
    __slots__ = ['pattern']

    def __init__(self, regex):
        super(r, self).__init__(regex)

        try:
            self.pattern = compile(regex)

        except sre_constants.error:
            raise ValueError('Passed invalid regex: {}'.format(regex))

    def __str__(self):
        return 'r\'{}\''.format(self.pattern.pattern)

    def parse(self, string, **kw):
        try:
            a = self.pattern.match(string)

        except TypeError:
            raise ParseError('Can match a non-string!')

        if a is None:
            string = replace_ignored(string, **kw)

            a = self.pattern.match(string)

            if a is None:
                raise ParseError('String: "{}" doesn\'t match pattern: "{}"'.format(string, self.pattern.pattern))

        string = cut_off([a.group(0)], string, **kw)

        check_whole(string, **kw)

        return string, [a.group(0)]


class group(ParserElement):
    __slots__ = ['e']

    def __init__(self, el):
        super(group, self).__init__('')

        self.e = el

    def __str__(self):
        return '[{}]'.format(self.e)

    def parse(self, string, **kw):
        string, a = self.e.parse(string, **kw)

        return string, [a]


class union(ParserElement):
    __slots__ = ['a', 'b']

    def __init__(self, a, b):
        super(union, self).__init__('')

        self.a = a
        self.b = b

    def __str__(self):
        return str(self.a) + ' | ' + str(self.b)

    def parse(self, string, **kw):
        try:
            string, a = self.a.parse(string, **kw)

        except ParseError:
            try:
                string, a = self.b.parse(string, **kw)

            except ParseError:
                raise ParseError(('Invalid syntax at: "{}"\n' + ' ' * 23 + 'Expecting: "{}"').format(string, self))

        check_whole(string, **kw)

        return string, a


class named(ParserElement):
    __slots__ = ['e', 'name']

    def __init__(self, element, name):
        super(named, self).__init__('')

        self.e = element
        self.name = name

    def __str__(self):
        return '({}, {})'.format(self.name, self.e)

    def parse(self, string, **kw):
        string, a = self.e.parse(string, **kw)

        check_whole(string, **kw)

        return string, [(self.name, a)]


class apply(ParserElement):
    __slots__ = ['e', 'f']

    def __init__(self, element, func):
        super(apply, self).__init__('')

        self.e = element
        self.f = func if type(func) in {list, tuple} else (func,)

    def __str__(self):
        return '{} // {}'.format(self.e, self.f)

    def parse(self, string, **kw):
        string, a = self.e.parse(string, **kw)

        a = r_zip(a, self.f)

        out = []

        for x in a:
            o = x[1](x[0])

            out.append(o)

        check_whole(string, **kw)

        return string, out


class counter(ParserElement):
    __slots__ = ['e', 'min', 'max']

    def __init__(self, element, minimal, maximal):
        super(counter, self).__init__('')

        self.min = minimal
        self.max = maximal
        self.e = element

    def parse(self, string, **kw):
        out = []

        for i in count():
            i += 1

            if i == self.max:
                break

            try:
                k = kw.copy()
                k['not_whole'] = True

                string, a = self.e.parse(string, **k)

                out += a

            except ParseError:
                if i < self.min:
                    raise ParseError('Invalid syntax at: "{}"'.format(string))

                else:
                    break

        check_whole(string, **kw)

        return string, out


class suppress(ParserElement):
    __slots__ = ['el']

    def __init__(self, element):
        super(suppress, self).__init__('')

        self.el = element

    def __str__(self):
        return 'suppress({})'.format(self.el)

    def parse(self, string, **kw):
        string, _ = self.el.parse(string, **kw)

        check_whole(string, **kw)

        return string, []


class debugged(ParserElement):
    __slots__ = ['e', 'f']

    def __init__(self, el, fn):
        super(debugged, self).__init__('')

        self.e = el
        self.f = fn

    def parse(self, string, **kw):
        self.f(self.e, string, **kw)

        return self.e.parse(string, **kw)


class optional(ParserElement):
    __slots__ = ['e']

    def __init__(self, element):
        super(optional, self).__init__('')

        self.e = element

    def parse(self, string, **kw):
        try:
            return self.e.parse(string, **kw)

        except ParseError:
            return string, []


class negative(ParserElement):
    __slots__ = ['e']

    def __init__(self, element):
        super(negative, self).__init__('')

        self.e = element

    def parse(self, string, **kw):
        try:
            self.e.parse(string, **kw)

        except ParseError:
            return string, []

        raise ParseError(('Syntax error at: "{}"\n' + ' ' * 23 + 'Expecting anything but: "{}"').format(string, self.e))


class take_out(ParserElement):
    __slots__ = ['e', 'name']

    def __init__(self, element, name):
        super(take_out, self).__init__('')

        self.e = element
        self.name = name

    def parse(self, string, **kw):
        string, a = self.e.parse(string, **kw)

        a = [x.value for x in a if type(x) is tuple and x[0] == self.name]

        out = []
        for x in a:
            if type(x) is list:
                out += x

            else:
                out.append(x)

        check_whole(string, **kw)

        return string, out


class combinator(ParserElement):
    __slots__ = ['a', 'b']

    def __init__(self, a, b):
        super(combinator, self).__init__('')

        self.a = a
        self.b = b

    def __str__(self):
        return str(self.a) + ' + ' + str(self.b)

    def parse(self, string, **kw):
        out = []

        try:
            k = {x: y for x, y in kw.items() if x != 'not_whole'}

            string, a = self.a.parse(string, **k, not_whole=True)

            out += a

        except ParseError:
            raise

        try:
            string, a = self.b.parse(string, **kw)

            out += a

        except ParseError:
            raise

        check_whole(string, **kw)

        return string, out


# Helpers

class expr(ParserElement):
    class Associativity:
        LEFT = 0
        RIGHT = 1

    class Type:
        UNARY = 0
        BINARY = 1

    def __init__(self, operand, operators, lp='(', rp=')'):
        super(expr, self).__init__('')

        for o in operators:
            if o[1] not in [0, 1]:
                raise ValueError('Invalid operand count!')

            elif o[2] not in [0, 1]:
                raise ValueError('Invalid associativity!')

        op = None

        for i, x in enumerate(operators):
            if op is None:
                op = x[0]

                if not isinstance(op, ParserElement):
                    op = s(op)

            else:
                op |= x[0]

        lp = s(lp).spr()
        rp = s(rp).spr()

        exp = ptr()

        factor = operand | [lp + exp + rp]

        exp &= factor + (op + factor)[0:]

        self.expr = exp
        self.ops = operators
        self.operand = operand

    def parse(self, string, **kw):
        kw = kw.copy()
        kw['not_whole'] = True

        string, a = self.expr.parse(string, **kw)

        a = associate(self.ops, a)

        if len(a) > 1:
            a = [a]

        check_whole(string, **kw)

        return string, a


class delim_lst(ParserElement):
    __slots__ = ['e', 's', 'aloc', 'min', 'max']

    def __init__(self, el, sep, at_least_one_comma=True, min=0, max=None):
        super(delim_lst, self).__init__('')

        self.e = el
        self.s = sep

        self.min = min
        self.max = max

        self.aloc = at_least_one_comma

    def parse(self, string, **kw):
        string, a = (self.e + (self.s + self.e)[self.min:self.max]).parse(string, **kw)

        if self.aloc:
            elements = []

            for x in a:
                try:
                    self.e.parse(x)

                    elements.append(x)

                except ParseError:
                    pass

            if len(elements) < 2:
                raise ParseError('Delimited list has no comma!')

        return string, a


# Pointer to parser element (can be used for recursive grammars)

class ptr(ParserElement):
    __slots__ = ['e']

    def __init__(self):
        super(ptr, self).__init__('')

        self.e = None

    def __iand__(self, other):
        self.e = other

        return self

    def parse(self, string, **kw):
        return self.e.parse(string, **kw)

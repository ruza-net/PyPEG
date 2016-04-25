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

    def parse(self, string, **kw):
        raise NotImplementedError()

    def test(self, string, **kw):
        try:
            self.parse(string, **kw)

            return True

        except ParseError:
            return False

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

            elif type(other) is set and len(other) == 1:
                other = g(list(other)[0])

            else:
                raise NotImplementedError()

        return combinator(self, other)

    def __mod__(self, other):
        if not isinstance(other, ParserElement):
            if type(other) is str:
                other = s(other)

            elif type(other) is list and len(other) == 1:
                other = group(other[0])

            elif type(other) is set and len(other) == 1:
                other = g(list(other)[0])

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

            elif type(other) is set and len(other) == 1:
                other = g(list(other)[0])

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

    def copy(self):
        return s(self.value)

    def r(self):
        return r(self.value)

    def __str__(self):
        return 's({})'.format(repr(self.value))

    def parse(self, string, **kw):
        if type(string) is not str:
            raise ParseError('Can\'t match non-string!')

        try:
            a = self.parse_token(string)

        except ParseError:
            try:
                string = replace_ignored(string, **kw)

                a = self.parse_token(string)

            except ParseError:
                raise ParseError(
                    'Invalid syntax at: "{}"\nExpecting: "{}"'.format(string, self.value))

        string = string[len(self.value):]

        check_whole(string, **kw)

        return string, [a]

    def parse_token(self, string):
        if string[:len(self.value)] != self.value:
            raise ParseError('Can\'t match a single token from: "{}"'.format(string))

        return self.value


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
        if type(string) is not str:
            raise ParseError('Can\'t match non-string!')

        a = self.pattern.match(string)

        if a is None:
            string = replace_ignored(string, **kw)

            a = self.pattern.match(string)

            if a is None:
                raise ParseError('String: "{}" doesn\'t match pattern: "{}"'.format(string, self.pattern.pattern))

        string = cut_off([a.group(0)], string, **kw)

        check_whole(string, **kw)

        return string, [a.group(0)]


class g(ParserElement):
    __slots__ = ['el']

    def __init__(self, el):
        super(g, self).__init__('')

        self.el = el

    def __str__(self):
        return 'g({})'.format(self.el)

    def parse(self, string, **kw):
        string, a = self.el.parse(string, **kw)

        if type(a) is list and len(a) > 1:
            a = [a]

        return string, a


class group(ParserElement):
    __slots__ = ['el']

    def __init__(self, el):
        super(group, self).__init__('')

        self.el = el

    def __str__(self):
        return '[{}]'.format(self.el)

    def parse(self, string, **kw):
        if type(string) is not str:
            raise ParseError('Can\'t match non-string!')

        string, a = self.el.parse(string, **kw)

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
        if type(string) is not str:
            raise ParseError('Can\'t match non-string!')

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
    __slots__ = ['el', 'name']

    def __init__(self, el, name):
        super(named, self).__init__('')

        self.el = el
        self.name = name

    def __str__(self):
        return '({}, {})'.format(self.name, self.el)

    def parse(self, string, **kw):
        if type(string) is not str:
            raise ParseError('Can\'t match non-string!')

        string, a = self.el.parse(string, **kw)

        check_whole(string, **kw)

        return string, [(self.name, a)]


class apply(ParserElement):
    __slots__ = ['el', 'fn']

    def __init__(self, el, fn):
        super(apply, self).__init__('')

        self.el = el
        self.fn = fn if type(fn) in {list, tuple} else (fn,)

    def __str__(self):
        return '{} // {}'.format(self.el, self.fn)

    def parse(self, string, **kw):
        if type(string) is not str:
            raise ParseError('Can\'t match non-string!')

        string, a = self.el.parse(string, **kw)

        a = r_zip(a, self.fn)

        out = []

        for x in a:
            o = x[1](x[0])

            out.append(o)

        check_whole(string, **kw)

        return string, out


class counter(ParserElement):
    __slots__ = ['el', 'min', 'max']

    def __init__(self, el, min_, max_):
        super(counter, self).__init__('')

        self.min = min_
        self.max = max_
        self.el = el

    def __str__(self):
        return '({})[{}:{}]'.format(self.el, self.min, self.max)

    def parse(self, string, **kw):
        if type(string) is not str:
            raise ParseError('Can\'t match non-string!')

        out = []

        k = kw.copy()
        k['not_whole'] = True

        i = 0

        for i in count():
            if i == self.max:
                break

            try:
                string, a = self.el.parse(string, **k)

                out += a

            except ParseError:
                break

        if i < self.min:
            raise ParseError('Invalid syntax at: {}!'.format(string))

        check_whole(string, **kw)

        return string, out


class suppress(ParserElement):
    __slots__ = ['el']

    def __init__(self, el):
        super(suppress, self).__init__('')

        self.el = el

    def __str__(self):
        return 'suppress({})'.format(self.el)

    def rev(self):
        return self.el

    def parse(self, string, **kw):
        if type(string) is not str:
            raise ParseError('Can\'t match non-string!')

        string, _ = self.el.parse(string, **kw)

        check_whole(string, **kw)

        return string, []


class debugged(ParserElement):
    __slots__ = ['el', 'fn']

    def __init__(self, el, fn):
        super(debugged, self).__init__('')

        self.el = el
        self.fn = fn

    def parse(self, string, **kw):
        if type(string) is not str:
            raise ParseError('Can\'t match non-string!')

        self.fn(self.el, string, **kw)

        return self.el.parse(string, **kw)


class optional(ParserElement):
    __slots__ = ['el']

    def __init__(self, el):
        super(optional, self).__init__('')

        self.el = el

    def parse(self, string, **kw):
        if type(string) is not str:
            raise ParseError('Can\'t match non-string!')

        try:
            return self.el.parse(string, **kw)

        except ParseError:
            return string, []


class negative(ParserElement):
    __slots__ = ['el']

    def __init__(self, el):
        super(negative, self).__init__('')

        self.el = el

    def parse(self, string, **kw):
        if type(string) is not str:
            raise ParseError('Can\'t match non-string!')

        try:
            self.el.parse(string, **kw)

        except ParseError:
            return string, []

        raise ParseError(
            ('Syntax error at: "{}"\n' + ' ' * 23 + 'Expecting anything but: "{}"').format(string, self.el))


class take_out(ParserElement):
    __slots__ = ['el', 'name']

    def __init__(self, el, name):
        super(take_out, self).__init__('')

        self.el = el
        self.name = name

    def parse(self, string, **kw):
        if type(string) is not str:
            raise ParseError('Can\'t match non-string!')

        string, a = self.el.parse(string, **kw)

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
        if type(string) is not str:
            raise ParseError('Can\'t match non-string!')

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

    __slots__ = ['expr', 'ops', 'operand']

    def __init__(self, operand, operators, lp='(', rp=')'):
        super(expr, self).__init__('')

        for o in operators:
            if o[1] not in [0, 1]:
                raise ValueError('Invalid operand count!')

            elif o[2] not in [0, 1]:
                raise ValueError('Invalid associativity!')

        b_op = None

        u_op_l = None  # A binary operator that stands at left from its operand.
        u_op_r = None  # A binary operator that stands at right from its operand.

        for i, x in enumerate(operators):
            if x[1] == expr.Type.BINARY:
                if b_op is None:
                    b_op = x[0]

                    if not isinstance(b_op, ParserElement):
                        b_op = s(b_op)

                else:
                    b_op |= x[0]

            else:
                if x[2] == expr.Associativity.LEFT:
                    if u_op_l is None:
                        u_op_l = x[0]

                        if not isinstance(u_op_l, ParserElement):
                            u_op_l = s(u_op_l)

                    else:
                        u_op_l |= x[0]

                else:
                    if u_op_r is None:
                        u_op_r = x[0]

                        if not isinstance(u_op_r, ParserElement):
                            u_op_r = s(u_op_r)

                    else:
                        u_op_r |= x[0]

        u_op_l = u_op_l[0:] if u_op_l is not None else EMPTY
        u_op_r = u_op_r[0:] if u_op_r is not None else EMPTY

        lp = s(lp).spr()
        rp = s(rp).spr()

        exp = ptr()

        factor_generic = operand | [lp + exp + rp]

        factor = u_op_l + factor_generic + u_op_r

        factor_alone = u_op_l + factor_generic

        exp &= factor_alone + (u_op_r + b_op + factor)[0:]

        self.expr = exp
        self.ops = operators
        self.operand = operand

    def parse(self, string, **kw):
        if type(string) is not str:
            raise ParseError('Can\'t match non-string!')

        kw = kw.copy()
        kw['not_whole'] = True

        string, a = self.expr.parse(string, **kw)

        a = associate(self.operand, self.ops, a)

        if len(a) > 1:
            a = [a]

        check_whole(string, **kw)

        return string, a


class delim_lst(ParserElement):
    __slots__ = ['el', 'expr']

    EXTRA_COMMA_ALLOWED = 1
    EXTRA_COMMA_REQUIRED = 2

    def __init__(self, el, sep, **kwargs):
        super(delim_lst, self).__init__('')

        extra_comma = kwargs.get('extra_comma', 1)

        min_c, max_c = kwargs.get('comma_count', [0, None])

        self.el = el

        self.expr = g(el) + (sep + g(el))[min_c:max_c]

        if extra_comma == 1:
            self.expr += sep.opt()

        elif extra_comma == 2:
            self.expr += sep

    def parse(self, string, **kw):
        if type(string) is not str:
            raise ParseError('Can\'t match non-string!')

        string, a = self.expr.parse(string, **kw)

        return string, a


# Pointer to parser element (can be used for recursive grammars)

class ptr(ParserElement):
    __slots__ = ['e']

    def __init__(self):
        super(ptr, self).__init__('')

        self.e = None

    def __str__(self):
        return '&{}'.format(id(self))

    def __iand__(self, other):
        self.e = other

        return self

    def parse(self, string, **kw):
        if type(string) is not str:
            raise ParseError('Can\'t match non-string!')

        return self.e.parse(string, **kw)


# Empty element - does nothing

@singleton
class EMPTY(ParserElement):
    def __init__(self):
        super(self.__class__, self).__init__('')

    def __str__(self):
        return '<EMPTY>'

    def parse(self, string, **kw):
        return string, []

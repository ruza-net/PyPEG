import sre_constants
from re import compile

from pypeg.utils import *

from itertools import count
from functools import reduce

from operator import add

__author__ = 'Jan Růžička'
__email__ = 'jan.ruzicka01@gmail.com'

__version__ = '0.1'

__all__ = ['ParseError', 'ParserElement', 's', 'r', 'g', 'G', 'group', 'combo', 'union', 'named', 'apply', 'libra',
           'counter', 'suppress', 'debugged', 'optional', 'negative', 'take_out', 'combinator', 'expr', 'delim_lst',
           'ind_block', 'ptr', 'EMPTY', 'trim_comments']

indent_level_force = None


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

            elif type(other) is tuple and len(other) == 1:
                other = G(g(other[0]))

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

    def __mul__(self, other):
        if type(other) is int:
            return reduce(add, [self] * other)

        elif type(other) is tuple and len(other) == 2:
            return observer(self, *other)

        else:
            raise NotImplementedError()

    def __truediv__(self, other):
        if not isinstance(other, ParserElement):
            if type(other) is str:
                other = s(other)

            elif type(other) is list and len(other) == 1:
                other = group(other[0])

            elif type(other) is set and len(other) == 1:
                other = g(list(other)[0])

            else:
                raise NotImplementedError()

        return libra(self, other)

    def __matmul__(self, other):
        if type(other) not in {list, tuple} or len(other) != 2:
            raise NotImplementedError()

        return debugged(self, *other)

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

    def __xor__(self, other):
        if isinstance(other, ParserElement):
            return longest(self, other)

        else:
            raise NotImplementedError()

    def __eq__(self, other):
        if type(other) is str:
            return named(self, other)

        elif isinstance(other, ParserElement):
            if type(self) is not type(other):
                return False

            if hasattr(self, 'el') and (not hasattr(other, 'el') or self.el != other.el):
                return False

            elif hasattr(self, 'a') and (not hasattr(other, 'a') or self.a != other.a or self.b != other.b):
                return False

            else:
                return self.value == other.value

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

        if item.stop is not None and -1 < item.stop < item.start:
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
        super(g, self).__init__(el.value)

        self.el = el

    def __str__(self):
        return 'g({})'.format(self.el)

    def parse(self, string, **kw):
        string, a = self.el.parse(string, **kw)

        if type(a) is list and len(a) > 1:
            a = [a]

        return string, a


class G(ParserElement):
    __slots__ = ['el']

    def __init__(self, el):
        super(G, self).__init__(el.value)

        self.el = el

    def __str__(self):
        return 'G({})'.format(self.el)

    def parse(self, string, **kw):
        string, a = self.el.parse(string, **kw)

        if len(a) == 0 or type(a[0]) not in {list, tuple}:
            a = [a]

        return string, a


class group(ParserElement):
    __slots__ = ['el']

    def __init__(self, el):
        super(group, self).__init__(el.value)

        self.el = el

    def __str__(self):
        return '[{}]'.format(self.el)

    def parse(self, string, **kw):
        if type(string) is not str:
            raise ParseError('Can\'t match non-string!')

        string, a = self.el.parse(string, **kw)

        return string, [a]


class combo(ParserElement):
    __slots__ = ['el']

    def __init__(self, el):
        super(combo, self).__init__(el.value)

        self.el = el

    def parse(self, string, **kw):
        string, a = self.el.parse(string, **kw)

        out = []

        for x in a:
            if len(out) == 0:
                out.append(x)

            elif isinstance(x, type(out[-1])):
                try:
                    out[-1] += x

                except AttributeError:
                    out.append(x)

            else:
                out.append(x)

        return string, out


class union(ParserElement):
    __slots__ = ['a', 'b']

    def __init__(self, a, b):
        super(union, self).__init__(a.value)

        self.a = a
        self.b = b

    def __str__(self):
        return '({} | {})'.format(self.a, self.b)

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
        super(named, self).__init__(el.value)

        self.el = el
        self.name = name

    def __str__(self):
        return '({}, {})'.format(self.name, self.el)

    def parse(self, string, **kw):
        if type(string) is not str:
            raise ParseError('Can\'t match non-string!')

        string, a = self.el.parse(string, **kw)

        check_whole(string, **kw)

        if len(a) == 1:
            a = a[0]

        return string, [(self.name, a)]


class apply(ParserElement):
    __slots__ = ['el', 'fn']

    def __init__(self, el, fn):
        super(apply, self).__init__(el.value)

        self.el = el
        self.fn = fn

    def __str__(self):
        return '{} // {}'.format(self.el, self.fn)

    def parse(self, string, **kw):
        if type(string) is not str:
            raise ParseError('Can\'t match non-string!')

        string, a = self.el.parse(string, **kw)

        check_whole(string, **kw)

        return string, map(self.fn, a)


class libra(ParserElement):
    __slots__ = ['a', 'b', 'merge']

    def __init__(self, a, b, merge=False):
        super(libra, self).__init__(a.value if len(a.value) > len(b.value) else b.value)

        self.a = a
        self.b = b

        self.merge = merge

    def __str__(self):
        return '{} / {} / {}'.format(self.a, self.b, self.merge)

    def __truediv__(self, other):
        if type(other) is bool:
            self.merge = other

            return self

        else:
            return libra(self, other)

    def parse(self, string, **kw):
        a_string, b_string = None, None

        try:
            a_string, a = self.a.parse(string, **kw)

        except ParseError:
            a = []

        if self.merge and a_string is not None:
            try:
                b_string, b = self.b.parse(a_string, **kw)

                return b_string, a + b

            except ParseError:
                try:
                    b_string, b = self.b.parse(string, **kw)

                except ParseError:
                    b = []

        else:
            try:
                b_string, b = self.b.parse(string, **kw)

            except ParseError:
                b = []

        if a_string is None or len(b_string) < len(a_string):
            return b_string, b

        elif b_string is None or len(a_string) < len(b_string):
            return a_string, a


class counter(ParserElement):
    __slots__ = ['el', 'min', 'max']

    def __init__(self, el, min_=0, max_=None):
        super(counter, self).__init__(el.value * min_)

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


class longest(ParserElement):
    __slots__ = ['a', 'b']

    def __init__(self, a, b):
        super(longest, self).__init__(b.value if len(b.value) > len(a.value) else a.value)

        self.a = a
        self.b = b

    def __str__(self):
        return '({} ^ {})'.format(self.a, self.b)

    def parse(self, string, **kw):
        kw = kw.copy()
        kw['not_whole'] = True

        s1 = s2 = string

        a1, a2 = [], []

        try:
            s1, a1 = self.a.parse(string, **kw)

        except ParseError:
            pass

        try:
            s2, a2 = self.b.parse(string, **kw)

        except ParseError:
            pass

        if len(s1) == len(s2) == len(string):
            raise ParseError('Both cases failed!')

        return (s1, a1) if len(s1) < len(s2) else (s2, a2)


class suppress(ParserElement):
    __slots__ = ['el']

    def __init__(self, el):
        super(suppress, self).__init__(el.value)

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
    __slots__ = ['el', 'a_fn', 'b_fn']

    def __init__(self, el, a_fn=None, b_fn=None):
        super(debugged, self).__init__(el.value)

        self.el = el

        self.a_fn = a_fn if a_fn else lambda el, string, **kw: print('A', el, repr(string))
        self.b_fn = b_fn if b_fn else lambda el, string, **kw: print('B', el, repr(string))

    def parse(self, string, **kw):
        if type(string) is not str:
            raise ParseError('Can\'t match non-string!')

        self.a_fn(self.el, string, **kw)

        string, a = self.el.parse(string, **kw)

        self.b_fn(self.el, string, **kw)

        return string, a


class optional(ParserElement):
    __slots__ = ['el']

    def __init__(self, el):
        super(optional, self).__init__('')

        self.el = el

    def __str__(self):
        return '({}).opt()'.format(self.el)

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
        super(take_out, self).__init__(el.value)

        self.el = el
        self.name = name

    def __str__(self):
        return str(self.el.el) if type(self.el) is named and self.el.name == self.name\
                               else '({} >> {})'.format(self.el, self.name)

    def parse(self, string, **kw):
        if type(string) is not str:
            raise ParseError('Can\'t match non-string!')

        string, a = self.el.parse(string, **kw)

        a = [x[1] for x in a if type(x) is tuple and x[0] == self.name]

        out = []
        for x in a:
            if type(x) is list:
                out += x

            else:
                out.append(x)

        check_whole(string, **kw)

        return string, out


class observer(ParserElement):
    __slots__ = ['el', 'success', 'failure']

    def __init__(self, el, success, failure):
        super(observer, self).__init__(el.value)

        if type(success) is not list:
            success = [success]

        if type(failure) is not list:
            failure = [failure]

        self.el = el
        self.success = success
        self.failure = failure

    def __str__(self):
        return 'observer({}, {}, {})'.format(self.el, self.success, self.failure)

    def parse(self, string, **kw):
        try:
            kw = kw.copy()
            kw['not_whole'] = True

            string, a = self.el.parse(string, **kw)

            return string, self.success if a else self.failure

        except ParseError:
            return string, self.failure


class combinator(ParserElement):
    __slots__ = ['a', 'b']

    def __init__(self, a, b):
        super(combinator, self).__init__(a.value + b.value)

        self.a = a
        self.b = b

    def __str__(self):
        return '{} + {}'.format(self.a, self.b)

    def parse(self, string, **kw):
        if type(string) is not str:
            raise ParseError('Can\'t match non-string!')

        out = []

        try:
            k = kw.copy()
            k['not_whole'] = True

            string, a = self.a.parse(string, **k)

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
        UNARY = 1
        BINARY = 2

    __slots__ = ['expr', 'ops', 'operand']

    def __init__(self, operand, operators, lp='(', rp=')'):
        super(expr, self).__init__('')

        for o in operators:
            if o[1] not in [1, 2]:
                raise ValueError('Invalid operand count!')

            elif o[2] not in [0, 1]:
                raise ValueError('Invalid associativity!')

        b_op = None

        b_op_lst = [x[0] for x in operators if x[1] == 2]

        u_op_l = None  # An unary operator that stands at left from its operand.
        u_op_r = None  # An unary operator that stands at right from its operand.

        for i, x in enumerate(operators):
            if x[1] == 2:
                if b_op is None:
                    b_op = x[0]

                    if not isinstance(b_op, ParserElement):
                        b_op = s(b_op)

                else:
                    b_op ^= x[0]

            elif x[0] not in b_op_lst:
                if x[2] == expr.Associativity.LEFT:
                    if u_op_l is None:
                        u_op_l = x[0]

                        if not isinstance(u_op_l, ParserElement):
                            u_op_l = s(u_op_l)

                    else:
                        u_op_l ^= x[0]

                else:
                    if u_op_r is None:
                        u_op_r = x[0]

                        if not isinstance(u_op_r, ParserElement):
                            u_op_r = s(u_op_r)

                    else:
                        u_op_r ^= x[0]

        u_op_l = u_op_l[0:] if u_op_l is not None else EMPTY
        u_op_r = u_op_r[0:] if u_op_r is not None else EMPTY

        lp = s(lp).spr()
        rp = s(rp).spr()

        exp = ptr()

        factor_generic = g(operand) | [lp + exp + rp]

        factor = u_op_l + factor_generic + u_op_r

        exp &= factor + (b_op + factor)[0:]

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

        req_one = kwargs.get('req_one', False)

        extra_comma = kwargs.get('extra_comma', 1)
        omit_blank = kwargs.get('omit_blank', False)
        min_c, max_c = kwargs.get('comma_count', [0, None])

        self.el = el

        if omit_blank:
            sep = sep[1:]

        if extra_comma == 1 and min_c > 0:
            self.expr = g(el) + (sep + g(el))[min_c:max_c] / sep / True

        else:
            if max_c is not None:
                max_c -= 1

            self.expr = g(el) + (sep + g(el))[min_c:max_c]

            if extra_comma == 1:
                self.expr += sep.opt()

            elif extra_comma == 2:
                self.expr += sep

            if req_one == 0:
                self.expr = self.expr.opt()

    def parse(self, string, **kw):
        if type(string) is not str:
            raise ParseError('Can\'t match non-string!')

        string, a = self.expr.parse(string, **kw)

        check_whole(string, **kw)

        return string, a


class ind_block(ParserElement):
    def __init__(self, el, char=' ', ch_count=4, sep=s('\n'), **kwargs):
        super(ind_block, self).__init__('')

        if type(char) is not str:
            raise TypeError('2nd argument `char` must be `str` (got `{}`)!'.format(type(char)))

        if type(sep) is str:
            sep = s(sep)

        self.el = el
        self.sep = sep
        self.ind = s(char * ch_count)

        self.options = kwargs

    def parse(self, string, **kw):
        lines = split(string, self.sep)

        i = 0

        for i, l in enumerate(lines):
            try:
                l, _ = self.ind.parse(l, not_whole=True)

                lines[i] = l

            except ParseError:
                break

        string = self.sep.value.join(lines)

        out = []

        j = 0

        while j < i:
            try:
                string, a = self.el.parse(string, **kw)

                out += a

            except ParseError:
                break

            j += 1

        return string, out


# Pointer to parser element (can be used for recursive grammars)

class ptr(ParserElement):
    __slots__ = ['el']

    def __init__(self):
        super(ptr, self).__init__('')

        self.el = None

    def __str__(self):
        return '&{}'.format(id(self))

    def __iand__(self, other):
        self.el = other

        return self

    def parse(self, string, **kw):
        if type(string) is not str:
            raise ParseError('Can\'t match non-string!')

        return self.el.parse(string, **kw)


# Empty element - does nothing

@singleton
class EMPTY(ParserElement):
    def __init__(self):
        super(self.__class__, self).__init__('')

    def __str__(self):
        return '<EMPTY>'

    def parse(self, string, **kw):
        return string, []

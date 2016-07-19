import sre_constants
from re import compile

from operator import add

from pypeg.utils import *

from itertools import count
from functools import reduce

__author__ = 'Jan Růžička'
__email__ = 'jan.ruzicka01@gmail.com'

__version__ = '0.1'

__all__ = ['ParseError', 'ParserElement', 's', 'r', 'u', 'g', 'G', 'cut', 'wrap', 'group', 'combo', 'union', 'named',
           'apply', 'libra', 'counter', 'suppress', 'debugged', 'optional', 'negative', 'take_out', 'combinator',
           'expr', 'delim_lst', 'ptr', 'EMPTY', 'trim_comments']

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

    def rev(self):
        if hasattr(self, 'el'):
            return self.el

        elif hasattr(self, 'a'):
            return self.a, self.b

        else:
            return self.value

    def __pos__(self):
        return combo(self)

    def __add__(self, other):
        other = to_valid_element(other)

        return combinator(self, other)

    def __mod__(self, other):
        other = to_valid_element(other)

        return other.spr() + self + other.spr()

    def __mul__(self, other):
        if type(other) is int:
            return reduce(add, [self] * other)

        elif type(other) is tuple and len(other) == 2:
            return observer(self, *other)

        else:
            raise NotImplementedError()

    def __truediv__(self, other):
        other = to_valid_element(other)

        return libra(self, other)

    def __matmul__(self, other):
        if type(other) is tuple:
            if len(other) == 0:
                other = (None, None)

            return debugged(self, *other)

        raise NotImplementedError()

    def __floordiv__(self, other):
        if not hasattr(other, '__call__') and len([x for x in other if not hasattr(x, '__call__')]) > 1:
            raise NotImplementedError()

        return apply(self, other)

    def __or__(self, other):
        other = to_valid_element(other)

        return union(self, other)

    def __xor__(self, other):
        other = to_valid_element(other)

        return longest(self, other)

    def __eq__(self, other):
        if type(other) is str:
            return named(self, other)

        elif isinstance(other, ParserElement):
            if type(self) is not type(other)\
                    or (hasattr(self, 'el') and (not hasattr(other, 'el') or self.el != other.el))\
                    or (hasattr(self, 'a') and (not hasattr(other, 'a') or self.a != other.a or self.b != other.b)):
                return False

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


class wrap:
    __slots__ = ['c', 't']

    class wrapper(ParserElement):
        __slots__ = ['el', 't', 'c']

        def __init__(self, el, t, c=2):
            super(wrap.wrapper, self).__init__(el.value)

            self.c = c
            self.t = t
            self.el = el

        def parse(self, string, **kw):
            string, a = self.el.parse(string, **kw)

            check_whole(string, **kw)

            if self.t in {'r', 'right'}:
                a = recursive_reverse(a)

            while len(a) > 1:
                a = [a[:self.c]] + a[self.c:]

            if self.t in {'r', 'right'}:
                a = recursive_reverse(a)

            return string, a

    def __init__(self, t, c=2):
        self.c = c
        self.t = t

    def __add__(self, other):
        other = to_valid_element(other)

        return wrap.wrapper(other, self.t, self.c)


class s(ParserElement):
    __slots__ = ['value']

    def __init__(self, value):
        super(s, self).__init__(value)

    def r(self):
        return r(self.value)

    def __str__(self):
        return 's{}'.format(repr(self.value))

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
        if not string.startswith(self.value):
            raise ParseError('Can\'t match a single token from: "{}"'.format(string))

        return self.value


class r(ParserElement):
    __slots__ = ['pattern']

    def __init__(self, pattern):
        super(r, self).__init__(pattern)

        try:
            self.pattern = compile(pattern)

        except sre_constants.error:
            raise ValueError('Passed invalid pattern: {}'.format(pattern))

    def __str__(self):
        return 'r\'{}\''.format(self.pattern.pattern)

    def parse(self, string, **kw):
        if type(string) is not str:
            raise ParseError('Can\'t match non-string!')

        a = self.pattern.match(string)
        b = self.pattern.match(replace_ignored(string, **kw))

        if a is None or (b is not None and len(a.group()) < len(b.group())):
            a = b

        if a is None:
            raise ParseError('String: "{}" doesn\'t match pattern: "{}"'.format(string, self.pattern.pattern))

        string = replace_ignored(string, **kw)[len(a.group()):] if a == b else string[len(a.group()):]

        check_whole(string, **kw)

        return string, [a.group()]


class u(ParserElement):
    __slots__ = ['el']

    def __init__(self, el):
        super(u, self).__init__(el.value)

        self.el = el

    def __str__(self):
        return 'u({})'.format(self.el)

    def parse(self, string, **kw):
        string, a = self.el.parse(string, **kw)

        if type(a) is list and len(a) == 1:
            a = a[0]

        return string, a


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
            if len(out) == 0 or not isinstance(x, type(out[-1])):
                out.append(x)

            else:
                try:
                    out[-1] += x

                except AttributeError:
                    out.append(x)

        return string, out


class union(ParserElement):
    __slots__ = ['xs']

    def __init__(self, *xs):
        super(union, self).__init__('')

        self.xs = []

        for x in xs:
            if type(x) is union:
                self.xs += x.xs

            elif x is not EMPTY:
                self.xs.append(x)

    def __str__(self):
        return ' | '.join([str(x) for x in self.xs])

    def __or__(self, other):
        other = to_valid_element(other)

        new = union(*self.xs)

        if type(other) is union:
            new.xs += other.xs

        elif other is EMPTY:
            pass

        else:
            new.xs.append(other)

        return new

    def parse(self, string, **kw):
        if type(string) is not str:
            raise ParseError('Can\'t match non-string!')

        for x in self.xs:
            try:
                return x.parse(string, **kw)

            except ParseError:
                pass

        raise ParseError('All cases failed!')


class named(ParserElement):
    __slots__ = ['el', 'name']

    def __init__(self, el, name):
        super(named, self).__init__(el.value)

        self.el = el
        self.name = name

    def __str__(self):
        return ':{}'.format(self.name)

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

        return string, list(map(self.fn, a))


class libra(ParserElement):
    __slots__ = ['xs', 'merge']

    def __init__(self, a, b, merge=False):
        super(libra, self).__init__('')

        self.xs = [a, b]

        self.merge = merge

    def __str__(self):
        return ' / '.join([str(x) for x in self.xs]) + ' / {}'.format(self.merge)

    def __truediv__(self, other):
        new = libra(*self.xs, merge=self.merge)

        if type(other) is bool:
            new.merge = other

        else:
            other = to_valid_element(other)

            if type(other) is libra and new.merge == other.merge:
                new.xs += other.xs

            elif other is EMPTY:
                pass

            else:
                new.xs.append(other)

        return new

    def parse(self, string, **kw):
        if self.merge:
            k = kw.copy()
            k['not_whole'] = True

            solutions = []

            for x in self.xs:
                string, a = x.parse(string, **k)

                solutions.append(a)

        else:
            solutions = {}

            for x in self.xs:
                try:
                    new_string, a = x.parse(string, **kw)

                    solutions[new_string] = a

                except ParseError:
                    pass

        if len(solutions) == 0:
            raise ParseError('All cases failed!')

        if self.merge:
            return string, reduce(add, solutions, [])

        ret = min(solutions.keys(), key=len)

        return ret, solutions[ret]


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
    __slots__ = ['xs']

    def __init__(self, *xs):
        super(longest, self).__init__('')

        self.xs = []

        for x in xs:
            if type(x) is longest:
                self.xs += x.xs

            else:
                self.xs.append(to_valid_element(x))

    def __str__(self):
        return ' ^ '.join([str(x) for x in self.xs])

    def __xor__(self, other):
        other = to_valid_element(other)

        new = longest(*self.xs)

        if type(other) is longest:
            new.xs += other.xs

        elif other is EMPTY:
            pass

        else:
            new.xs.append(other)

        return new

    def parse(self, string, **kw):
        solutions = {}

        for x in self.xs:
            try:
                new_string, a = x.parse(string, **kw)

                solutions[new_string] = a

            except ParseError:
                pass

        if len(solutions) == 0:
            raise ParseError('All cases failed!')

        ret = min(solutions.keys(), key=len)

        return ret, solutions[ret]


class suppress(ParserElement):
    __slots__ = ['el']

    def __init__(self, el):
        super(suppress, self).__init__(el.value)

        self.el = el

    def __str__(self):
        return '{}.spr()'.format(self.el)

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

        self.a_fn = a_fn if a_fn else lambda e, string, **kw: print('A', e, repr(string))
        self.b_fn = b_fn if b_fn else lambda e, string, **kw: print('B', e, repr(string))

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

    def __str__(self):
        return '!{}'.format(self.el)

    def parse(self, string, **kw):
        if type(string) is not str:
            raise ParseError('Can\'t match non-string!')

        try:
            self.el.parse(string, **kw)

        except ParseError:
            return string, []

        raise ParseError('Syntax error at: "{}"\nExpecting anything but: "{}"'.format(string, self.el))


class take_out(ParserElement):
    __slots__ = ['el', 'name']

    def __new__(cls, *args):
        if type(args[0]) is named:
            return args[0].el

        return super(take_out, cls).__new__(cls)

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
    __slots__ = ['xs']

    def __init__(self, *xs):
        super(combinator, self).__init__('')

        self.xs = []

        for x in xs:
            if type(x) is combinator:
                self.xs += x.xs

            elif x is not EMPTY:
                self.xs.append(to_valid_element(x))

    def __str__(self):
        return ' + '.join([str(x) for x in self.xs])

    def __add__(self, other):
        other = to_valid_element(other)

        new = combinator(*self.xs)

        if type(other) is combinator:
            new.xs += other.xs

        elif other is EMPTY:
            pass

        else:
            new.xs.append(other)

        return new

    def parse(self, string, **kw):
        if type(string) is not str:
            raise ParseError('Can\'t match non-string!')

        k = kw.copy()
        k['not_whole'] = True

        out = []

        fatal = False

        for x in self.xs:
            if x is cut:
                fatal = True

            else:
                try:
                    string, a = x.parse(string, **k)

                    out += a

                except ParseError as e:
                    if fatal:
                        raise FatalParseError(str(e))

                    raise

        check_whole(string, **kw)

        return string, out


# Helpers

class expr(ParserElement):
    __slots__ = ['expr', 'ops', 'operand']

    def __init__(self, operand, operators, lp='(', rp=')'):
        for o in operators:
            if o[1] not in [1, 2]:
                raise ValueError('Invalid operand count!')

            elif o[2] not in [0, 1, 2]:
                raise ValueError('Invalid associativity!')

        b_op = None

        u_op_l = None

        for x in operators:
            if x[1] == 2:
                if b_op is None:
                    b_op = to_valid_element(x[0])

                else:
                    b_op ^= x[0]

            elif u_op_l is None:
                u_op_l = to_valid_element(x[0])

            else:
                u_op_l ^= x[0]

        u_op_l = u_op_l[0:] if u_op_l is not None else EMPTY

        lp = to_valid_element(lp).spr()
        rp = to_valid_element(rp).spr()

        exp = ptr()

        factor = g(operand) ^ [lp + exp + rp]

        factor = factor ^ u_op_l + factor

        exp &= factor + (b_op + factor)[0:]

        self.expr = exp
        self.ops = operators
        self.operand = operand

        super(expr, self).__init__(exp.value)

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
    __slots__ = ['expr']

    EXTRA_COMMA_ALLOWED = 1
    EXTRA_COMMA_REQUIRED = 2

    def __init__(self, el, sep, *, req_one=False, extra_comma=1, omit_blank=False, comma_count=None):
        min_c, max_c = [0, None] if comma_count is None else comma_count

        el = g(el)

        if omit_blank:
            el = el.opt()

        if extra_comma == 1 and min_c > 0:
            self.expr = el + (sep + el)[min_c:max_c] / sep / True

        else:
            if max_c is not None:
                max_c -= 1

            self.expr = el + (sep + el)[min_c:max_c]

            if extra_comma == 1:
                self.expr += sep.opt()

            elif extra_comma == 2:
                self.expr += sep

            if not req_one:
                self.expr = self.expr.opt()

        super(delim_lst, self).__init__(self.expr.value)

    def parse(self, string, **kw):
        if type(string) is not str:
            raise ParseError('Can\'t match non-string!')

        string, a = self.expr.parse(string, **kw)

        check_whole(string, **kw)

        return string, a


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


# Cutting element - when it gets invoked, any error becomes fatal.

@singleton
class cut(ParserElement):
    def __init__(self):
        super(self.__class__, self).__init__('')

    def __str__(self):
        return '<CUT>'

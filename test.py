from pypeg import *

__author__ = 'Jan Růžička'
__email__ = 'jan.ruzicka01@gmail.com'

__version__ = '0.1'


def main():
    operators = {'+': lambda x, y: x + y, '-': lambda x, y: x - y, '*': lambda x, y: x * y, '/': lambda x, y: x / y}

    def parse_expr(tree):
        accumulator = None

        for i, x in enumerate(tree):
            if i % 2 == 0:
                if accumulator is None:
                    accumulator = x

                else:
                    accumulator = operators[tree[i-1]](accumulator, x)

        return accumulator

    n = s('[+\-]?[0-9]+(\.[0-9]+)?([eE][+\-][0-9]+)?').r() // float
    o = s('+') | '-' | '*' | '/'

    expr = n + (o + n)[1:]

    ast = expr.parse('1 + 2 - 3 * 4 / 5', ignore=' ')[1]

    print(ast)


if __name__ == '__main__':
    main()

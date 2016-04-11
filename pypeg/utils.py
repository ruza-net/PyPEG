from itertools import cycle

__author__ = 'Jan Růžička'
__email__ = 'jan.ruzicka01@gmail.com'

__version__ = '0.1'


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

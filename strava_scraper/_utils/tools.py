# Higher-order functions

import functools

def identity(x):
    return x

def find(predicate, iterable):
    for i in filter(predicate, iterable):
        return i
    return None

def first(xs, mapper=lambda x:x):
    if len(xs) > 0: return mapper(xs[0])

def each(xs, mapper=lambda x:x):
    for x in xs:
        yield mapper(x)

def non_match(xs, predicate):
    for x in xs:
        if not predicate(x): return True
    return False

def any_match(xs, predicate):
    for x in xs:
        if predicate(x): return True
    return False

def conjonction(a, b):
    return lambda value: a(value) and b(value)

def disjonction(a, b):
    return lambda value: a(value) or b(value)

def all_predicates(predicates):
    return functools.reduce(conjonction, predicates, lambda x: True)

def id_eq(a):
    return lambda b: a.id == b.id


# Predicates
def contains(param, value):
    if not param or len(param) == 0:
        return True
    if len(param) > 1 and param[0] == '-':
        return param[1:].lower() not in value.lower()

    return param.lower() in value.lower()

def eq(param, value):
    if not param or len(param) == 0:
        return True
    if len(param) > 1 and param[0] == '-':
        return param[1:].lower() != value.lower()

    return param.lower() == value.lower()

def eq_bool(param, value):
    if param == None:
        return True

    return param == value

from random import randint


def rand_chance(how_many, from_amount):
    return randint(1, from_amount) < how_many


def throw_coin():
    return rand_chance(1, 2)


def str_indent(indent):
    return ' ' * indent

from string import Formatter


def get_path(route):
    return route.rule


def get_path_keys(path):
    return [i[1] for i in Formatter().parse(path) if i[1]]


def issubclass_py37fix(cls, cls_info):
    try:
        return issubclass(cls, cls_info)
    except TypeError:
        return False

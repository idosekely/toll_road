__author__ = 'sekely'


def parse_arg(arg_name, args, arg_type=None, default_val=None):
    arg = args.get(arg_name, default_val)
    if isinstance(arg, list):
        arg = arg[0]
    if arg_type:
        return arg_type(arg)
    return arg


class ServerStopped(Exception):
    pass


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]

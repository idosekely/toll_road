from functools import wraps
__author__ = 'sekely'


def parse_single_arg(arg_name, args, arg_type=None, default_val=None):
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


def parse_args(**k):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            pv = {}
            for key, val in k.iteritems():
                arg_type, default_val = val
                pv[key] = parse_single_arg(key, kwargs, arg_type, default_val)
            kwargs.update(pv)
            return func(*args, **kwargs)
        return wrapper
    return decorator

def safe(wrapped):

    @wraps(wrapped)
    def wrapper(*args, **kwargs):
        try:
            wrapped(*args, **kwargs)
        except ServerStopped as e:
            raise e
        except Exception as e:
            print e
    return wrapper


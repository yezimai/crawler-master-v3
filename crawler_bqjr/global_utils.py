try:
    from ujson import loads as json_loads, dumps as json_dumps
except ImportError:
    from json import loads as json_loads, dumps as json_dumps


# 单例元类
class Singleton(type):
    def __init__(cls, *args, **kwargs):
        super().__init__(*args, **kwargs)
        cls.__instance = None

    def __call__(cls, *args, **kwargs):
        if cls.__instance is None:
            cls.__instance = super().__call__(*args, **kwargs)
        return cls.__instance

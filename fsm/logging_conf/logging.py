import collections
import logging
import sys
from copy import copy
from typing import TypeVar, Dict, Callable

# from colorlog import colorlog

A = TypeVar('A')
B = TypeVar('B')


class DynamicDict(collections.abc.Mapping):
    """
    A dictionary like object that contains static key/value and static key to dynamic value mappings.
    This allows to get dynamic values on every lookup.
    Intended to be used as `extra` fields in logging adapter.
    Note that dynamic values are not thread safe.
    """
    def __init__(self, static_dict: Dict[A, B], dynamic_dict: Dict[A, Callable[[], B]]) -> None:
        self.sdict = {k: v for k, v in static_dict.items() if v or k not in dynamic_dict}
        self.ddict = copy(dynamic_dict)
        self.len = len(self.sdict) + len(self.ddict)

    def __len__(self) -> int:
        return self.len

    def __getitem__(self, item: A) -> B:
        opt = self.sdict.get(item, '')
        return opt if opt != '' else self.ddict[item]()

    def __iter__(self):
        from itertools import chain
        return chain(iter(self.sdict), iter({k: v() for k, v in self.ddict.items()}))


default_format = '%(log_color)s[%(levelname)s]%(reset)s %(asctime)s - %(threadName)s - %(name)s - %(tenant)s - ' \
                 '%(runid)s - %(jobid)s - %(message)s'

default_extra = {'tenant': None, 'runid': None, 'jobid': None}


def get_root_app_logger(name: str, extra: Dict[A, B] = default_extra,
                        log_format: str = default_format) -> logging.LoggerAdapter:
    """
    Creates an application level "root" logger with a new handler. This logger should be a parent logger for all
    other logs created within application. There is one more parent logger above this logger - the actual root logger.
    Note that this logger doesn't propagate records to its parent (root logger) since it has extended format with
    `extra` fields.
    :param log_format: desired logging format. This should match `extra` fields provided.
    :param name: application level log name. All child logs will be prefixed with this name followed by dot.
    :param extra: additional static fields as specified in the logging format. Child loggers can override those later.
    :return:
    """
    loggr = logging.getLogger(name)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel("DEBUG")
    # formatter = colorlog.ColoredFormatter(log_format, reset=True, log_colors={
    #         'DEBUG': 'cyan',
    #         'INFO': 'green',
    #         'WARNING': 'yellow',
    #         'ERROR': 'red',
    #         'CRITICAL': 'red'
    #     })
    # handler.setFormatter(formatter)
    loggr.addHandler(handler)
    loggr.propagate = False
    log = logging.LoggerAdapter(loggr, copy(extra))
    return log


def add_dynamic_fields_to_logger(logger: logging.LoggerAdapter, dynamic_field_gen: Dict[A, Callable[[], B]]) -> None:
    """Adds `extra` fields to logger adapter which have to be evaluated every time by calling a provided function, hence
    dynamic fields. Check that these fields match log format, otherwise they won't be used.
    Note that previous fields in `extra` will take precedence over the ones you are adding with this call.
    Your new fields will be used only if previous `extra` fields map to None values or don't exist.
    :param logger
    :param dynamic_field_gen
    """
    logger.extra = DynamicDict(logger.extra, dynamic_field_gen)


def get_child_logger(app_root_logger_name: str, name: str, extra: Dict[A, B] = {}) -> logging.LoggerAdapter:
    """
    Creates a child logger of application level root logger. The format of this logger is defined by parent.
    :param app_root_logger_name: the application level root logger name that you define with `get_root_app_logger`.
    :param name: Name of this logger. Parent name will be prefixed with a dot.
    :param extra: These are additional extra values which are not required, but can be used as long as logging format
    references them.
    Required parameters for our application are: `tenant`, `runid`, `jobid`, which will be set to None
    unless any of these values are provided. It will depend on context whether you have any of these values to configure
    logger.
    :return: logging adapter that you can use for all logging needs within your module/context where extra values
    make sense and stay true.
    """
    loggr = logging.getLogger("{}.{}".format(app_root_logger_name, name))
    log = logging.LoggerAdapter(loggr, {**default_extra, **extra})
    return log

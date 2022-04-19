# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2021/09/23 11:51
"""


def create_logger(log_file, name='logger', cmd=True, level="info"):
    """define a logger for your program

    :param log_file: file name of log
    :param name: name of logger
    :param cmd: output in cmd
    :param level: level
    :return: logger
    """
    import logging

    level_map = {
        "info": logging.INFO,
        "debug": logging.DEBUG,
        "error": logging.ERROR,
    }
    log_level = level_map.get(level, logging.INFO)
    logger = logging.getLogger(name)
    logger.setLevel(log_level)

    # set format
    formatter = logging.Formatter('%(asctime)s | %(name)s | %(levelname)s | %(message)s',
                                  datefmt='%Y-%m-%d %H:%M:%S')

    # file handler
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(log_level)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    # cmd handler
    if cmd:
        ch = logging.StreamHandler()
        ch.setLevel(log_level)
        ch.setFormatter(formatter)
        logger.addHandler(ch)

    return logger




#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Date    : 2016-12-26 10:27:26
# @Author  : Li Hao (howardlee_h@outlook.com)
# @Link    : https://github.com/SAmmer0
# @Version : $Id$

'''
本程序用于对一些数据进行常用的预处理
__version__ = 1.0

修改日期：2016年12月26日
修改内容：
    添加基本函数gen_pdcolumns

__version__ = 1.1
修改日期：2017年1月4日
修改内容：
    添加在数据库中股票代码后添加后缀的函数add_suffix

__version__ 1.2
修改日期：2017年1月13日
修改内容：
    添加map_data函数

__version__ 1.3
修改日期：2017年1月18日
修改内容：
    修复了map_data中的BUG，使其能够正确返回交叉时间段内的数据结果
修改日期：2017-03-07
修改内容：
    1. 重构了map_data，使用更精简的函数实现
    2. 加入存储和读取pickle数据的函数load_pickle、dump_pickle

__version__ = 1.4
修改日期：2017年3月29日
修改内容：
    1. 从processsingdata中转移而来
    2. 添加retfreq_trans函数
    3. 添加annualize_std函数
'''
__version__ = 1.4

import datetime as dt
from math import sqrt
import numpy as np
import pandas as pd
import pickle
# import six


def gen_pdcolumns(data, operations):
    '''
    用于在data中添加新的列
    @param:
        data: 原始数据，要求为pd.DataFrame的格式
        operations: 需要添加的列，格式为{'colName': (func, {parameter dict})}或者{'colName': func}
            其中，func表示需要对数据进行处理的函数，要求函数只能调用每一行的数据，返回一个结果，且func
            的第一个参数为行数据，其他参数通过key=value的形式调用
    @return:
        res: 返回一个新的数据集，因为修改不是在原数据上进行的，因此需要采用以下方式才能将结果影响到原
            数据：data = gen_pdcolumns(data, operations)
    '''
    assert isinstance(data, pd.DataFrame), ('Parameter \"data\"" type error! Request ' +
                                            'pd.DataFrame, given %s' % str(type(data)))
    assert isinstance(operations, dict), ('Parameter \"operations\" type error! Request dict,' +
                                          'given %s' % str(type(operations)))
    res = data.copy()
    for col in operations:
        assert isinstance(col, str), 'Column name should be str, given %s' % str(type(col))
        operation = operations[col]
        if hasattr(operation, '__len__'):   # 表明为列表或其他列表类的类型
            assert len(operation) == 2, ('Operation paramter error! Request formula should like' +
                                         '(func, {parameter dict})')
            func = operation[0]
            params = operation[1]
            res[col] = res.apply(lambda x: func(x, **params), axis=1)
        else:
            res[col] = res.apply(func, axis=1)
    return res


def add_suffix(code):
    '''
    从数据库中获取的股票代码添加后缀，以60开头的代码添加.SH，其他添加.SZ
    @param:
        code: 需要转换的代码
    @return:
        转换后的代码
    注：转换前会检测是否需要转换，但是转换前不会检测代码是否合法
    '''
    if code.endswith('.SH') or code.endswith('.SZ'):
        return code
    if code.startswith('60'):   #
        suffix = '.SH'
    else:
        suffix = '.SZ'
    return code + suffix


def drop_suffix(code, suffixLen=3, suffix=('.SH', '.SZ')):
    '''
    将Wind等终端获取的数据的后缀转换为数据库中无后缀的代码
    @param:
        code: 需要转换的代码
        suffixLen: 后缀代码的长度，包含'.'，默认为3
        suffix: 后缀的类型，默认为('.SH', '.SZ')
    @return:
        转换后的代码
    '''
    for s in suffix:
        if code.endswith(s):
            break
    else:
        return code
    return code[:-suffixLen]


def map_data(rawData, days, timeCols='time', fromNowOn=False):
    '''
    将给定一串时点的数据映射到给定的连续时间上，映射规则如下：
    若fromNowOn为True时，则在rawData中给定时点以及该时点后的时间的值等于该时点的值，因此第一个日期无论
    其是否为数据更新的时间点，都会被抛弃
    若fromNowOn为False时，则在rawData中给定时点后的时间的值等于该时点的值
    最终得到的时间序列数据为pd.DataFrame的格式，数据列为在当前时间下，rawData中所对应的最新的值，对应
    方法由映射规则给出
    例如：若rawData中包含相邻两项为(2010-01-01, 1), (2010-02-01, 2)，且fromNowOn=True，则结果中，从
    2010-01-01起到2010-02-01（不包含当天）的对应的值均为1，若fromNowOn=False，则结果中，从2010-01-01
    （不包含当天）起到2010-02-01对应的值为1
    注：该函数也可用于其他非时间序列的地方，只需要有序列号即可，那么rowData的数据应为[(idx, value), ...]
    @param:
        rawData: 为pd.DataFrame格式的数据，要求包含timeCols列
        days: 所需要映射的日期序列，要求为列表或者其他可迭代类型（注：要求时间格式均为datetime.datetime）
        timeCols: 时间列的列名，默认为time
        fromNowOn: 默认为False，即在给定日期之后的序列的值才等于该值
    @return:
        pd.DataFrame格式的处理后的数据，数据长度与参数days相同，且时间列为索引
    '''
    if not isinstance(days, list):
        days = list(days)
    time_col = rawData[timeCols].tolist()
    time_col = [t for t in time_col if t < days[0]] + days
    data = rawData.set_index(timeCols)
    data = data.sort_index()
    data = data.reindex(time_col, method='ffill')
    if not fromNowOn:
        data = data.shift(1)
    data = data.reindex(days)
    return data


def date_processing(date, dateFormat=None):
    '''
    用于检查日期的类型，如果为str则转换为datetime的格式
    @param:
        date: 输入的需要处理的日期
        dateFormat: 日期转换的格式，默认为None，表示格式为YYYY-MM-DD
    @return:
        按照转换方法转换后的格式
    '''
    if dateFormat is None:
        dateFormat = '%Y-%m-%d'
    if not isinstance(date, dt.datetime):
        date = dt.datetime.strptime(date, dateFormat)
    return date


def load_pickle(path):
    '''
    读取pickle文件
    '''
    with open(path, 'rb') as f:
        return pickle.load(f)


def dump_pickle(data, path):
    '''
    将数据写入到pickle文件中
    '''
    with open(path, 'wb') as f:
        pickle.dump(data, f)


def retfreq_trans(init_ret, new_freq):
    '''
    将收益的频率进行转换，例如将日收益率转化为年化或者将年化收益率转化为日收益率
    计算方法如下：
    new_ret = (1 + init_ret)**(new_freq/init_freq) - 1
    @param:
        init_ret: 初始的需要转换的收益率
        new_freq: 最终收益率的频率，例如，月度数据年化则设为12
    @return:
        转换频率后的收益率
    '''
    return (1 + init_ret)**new_freq - 1


def annualize_std(init_std, init_ret, period_num):
    '''
    计算年化的波动率
    计算方法如下：
    new_std = sqrt((init_std**2 + (1+init_ret)**2)**period_num - (1+init_ret)**(2*period_num))
    @param:
        init_std: 初始需要转换的波动率
        init_ret: 初始频率的平均收益率
        period_num: 一年的区间数（例如，12表示月度数据年化）
    @return:
        按照上述方法计算的年化波动率
    '''
    return sqrt((init_std**2 + (1 + init_ret)**2)**period_num - (1 + init_ret)**(2 * period_num))


if __name__ == '__main__':
    pass
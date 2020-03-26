#！/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
Configuration
'''

__author__ = 'Han'

import config_default

class Dict(dict):
    '''
    Simple dict but support access as x.y style.
    '''
    def __init__(self, names=(),values=(), **kw):
        super(Dict, self).__init__(**kw)
            for k, v in zip(names, values):
                self[k] = v
                
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(r"'Dict' object has no attributte '%s'" % key)
            
    def __setattr__(self, key, value):
        self[key] = value

def merge(defaults, override): #把defaults里的多层字典全部打开为一层字典，即一个关键字对应一个value（非字典）,并且把OVERRIDE里的内容更新到defaults里
    r = {}
    for k, v in defaults.items():
        if k in override:
            if isinstance(v, dict):
                r[k] = merge(v, override[k])
            else:
                r[k] = override[k]
        else:
            r[k] = v
    return r
    
def toDict(d): #把defaults里的多层字典全部打开为一层字典，即一个关键字对应一个value（非字典
    D = Dict()
    for k, v in d.items():
        D[k] = toDict(v) if isinstance(v, dict) else v
    return D
    
configs = config_default.configs

try:
    import config_override
    configs = merge(configs, config_override.configs)
except ImportError:
    pass
    
configs = toDict(configs)
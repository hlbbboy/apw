#!/usr/bin/env python3
# -*-coding : utf-8 -*-

import asyncio, aiomysql, logging

#from orm import  Model, StringField, IntegerField

def log(sql, args=()):
    logging.info('SQL: %s' % sql)

async def create_pool(loop, **kw):
    logging.info('Create database connection pool...')
    global __pool
    __pool = await aiomysql.create_pool(
        host=kw.get('host', 'localhost'),
        port=kw.get('port', 3306),
        user=kw['user'],
        password=kw['password'],
        db=kw['db'],
        charset=kw.get('charset','utf-8'),
        autocommit=kw.get('autocommit', True),
        maxsize=kw.get('maxsize', 10),
        minisize=kw.get('minisize', 1),
        loop=loop
    )
    
async def select(sql, args, size=None):
    log(sql, args)
    global __pool
    async with __pool.get() as conn:
        #cur = await conn.cursor(aiomysql.DictCursor)
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(sql.replace('?', '%s'), args or ())
            if size:
                rs = await cur.fetchmany(size)
            else:
                rs = await cur.fetchall()
            #await cur.close()
            logging.info('rows returned: %s' % len(rs))
            return rs
        
async def execute(sql, args, autocommit=True):
    log(sql)
    #global __pool
    async with  __pool.get() as conn:
        if not autocommit:
            await conn.begin() #where does this method come from? pymysql from aiomysql
        try:
            async with  conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(sql.replace('?', '%s'), args)
                affected = cur.rowcount
            if not autocommit:
                await conn.commit()
        except BaseException as e:
            if not autocommit:
                await conn.rollback()
            raise
        return affected
 
def create_args_string(num):
    L = []
    for n in range(num):
        L.append('?')
    return ', '.join(L)
    
"""
class User(Model):
    __table__= 'users'
    id = IntegerField(name = 'id', primary_key = True)
    name = StringField(name = 'name') 
"""    
    
class Model(dict, metaclass=ModelMetaclass):
    
    def __init__(self, **kw):
        super(Model, self).__init__(**kw)

    def __getattr__(self, key):
        try:
            return self[key]
         except KeyError:
            raise AttributeError(r"'Model' object has no attribute '%s'" % key)
     
     def __setattr__(self, key, value):
        self[key] = value
        
     def getValue(self, key):
        return getattr(self, key, None)
        
    def getValueOrDefault(self, key):
        value = getattr(self, key, None)
        if value is None:
            field = self.__mappings__[key]
            if field.default is not None:
                value = field.default() if callable(field.default) else field.default
                logging.debug('using default value for %s: %s' % (key, str(value))
        return value 
        
class Field(object):
    
    def __init__(self, name, column_type, primary_key, default):
        self.name=name
        self.column_type=column_type
        self.primary_key=primary_key
        self.default=default
        
    def __str__(self):
        return '<%s, %s: %s>' % (self.__class__.__name__, self.column_type, self.name)

class StringField(Field):
    
    def __init__(self, name=None, ddl='varchar(100)',primary_key=False, default=None):
        super().__init__(name, ddl, primary_key, default)
        
class IntegerField(Field):

    def __init__(self, name=None, ddl='bigint', primary_key=False, default=None):
        super().__init__(name, ddl, primary_key, default)
        
class ModelMetaclass(type):

    def __new__(cls, name, base, attrs):
        if name == 'Model':
            return type.__new__(cls, name, bases, attrs)
        tableName = attrs.get('__table__', None) or name
        logging.info('found model: %s (table: %s)' % (name, tableName))
        mappings = dict()
        fields = []
        primaryKey = None
        for k, v in attrs.items():
            if isinstance(v, Field):
                logging.info('found mapping: %s==> %s' %(k, v))
                mappings[k] = v
                if v.primary_key:
                    if primaryKey:
                        raise StandardError('Duplicate primary key for field : %s' % k)
                    primaryKey = k
                else:
                    fields.append(k)
        if not primaryKey:
            raise StandardError('Primary key is not found.')
        for k in mappings.keys():
            attrs.pop(k)
        escape_fields = list(map(lambda f: '%s' % f, fields))
        attrs['__mappings__'] = mappings
        attrs['__table__'] = tableName
        attrs['__primary_key__'] = primaryKey
        attrs['__fields__'] = fields
        attrs['__select__'] = 'select `%s`, %s from `%s`' % (primaryKey, ', '.join(escape_fields), tableName)#这里要测试一下`符号的作用
        attrs['__insert__'] = 'insert into `%s` (%s, `%s`) values (%s)' % (tableName, ', 'join(escape_fields), primaryKey, create_args_string(len(escape_fields)+1))
        attrs['__update__'] = 'update `%s` set %s where %s = ?' % (tableName, ', '.join(map(lambda f: '`%s` = ?' % (mappings.get(f).name or f),fields)), primaryKey)
        attrs['__delete__'] = 'delete from `%s` where `%s` = ?' % (tableName, primaryKey)
        return type.__new__(cls, name, bases, attrs)
        
        
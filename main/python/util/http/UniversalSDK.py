# -*- coding:utf-8 -*-
__author__ = 'LiuYang'
__version__ = '1.0.0'

import json,urllib2,urllib,gzip,collections
from src.main.python.util.common.Decorators import retry
import logging
logger = logging.getLogger('ahu')

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO


class APIClient(object):
    domain = ""

    def __init__(self,domain):
        self.domain = domain

    def __getattr__(self,attr):
        return _Callable('%s/%s'%(self.domain,attr))

class _Callable(object):
    def __init__(self,client):
        self.client = client

    def __getattr__(self,attr):
        @retry((urllib2.URLError,ValueError), tries=10, delay=1, backoff=2)
        def execute(**kw):
            params = '%s'%(_encode_params(**kw))
            if len(params)!=0:
                http_url = '%s?%s'%(self.client,params) if self.method=='get' else self.client
            else:
                http_url =  self.client
            http_body = None if self.method == 'get' else params
            # print http_url
            # logging.info(http_url)
            req = urllib2.Request(http_url,data=http_body)
            req.add_header('Accept-Encoding', 'gzip')

            try:
                resp = urllib2.urlopen(req,timeout=25)
                body = _read_body(resp)
                r = _parse_json(body)
                return r
            except Exception as e:
                logging.error(e)
                pass

        def addTrail(trail):
            return _Callable('%s%s'%(self.client,trail))

        if attr == 'get':
            self.method = 'get'
            return execute
        if attr == 'post':
            self.method = 'post'
            return execute
        if attr == 'addtrail':
            return addTrail
        return _Callable('%s/%s'%(self.client,attr))


def _parse_json(s):
    ' parse str into JsonDict '

    def _obj_hook(pairs):
        ' convert json object to python object '
        o = JsonDict()
        for k, v in pairs.iteritems():
            o[str(k)] = v
        return o
    return json.loads(s, object_hook=_obj_hook)

class JsonDict(dict):
    ' general json object that allows attributes to be bound to and also behaves like a dict '

    def __getattr__(self, attr):
        try:
            return self[attr]
        except KeyError:
            raise AttributeError(r"'JsonDict' object has no attribute '%s'" % attr)

    def __setattr__(self, attr, value):
        self[attr] = value

def _encode_params(**kw):
    '''
    do url-encode parameters

    >>> _encode_params(a=1, b='R&D')
    'a=1&b=R%26D'
    >>> _encode_params(a=u'\u4e2d\u6587', b=['A', 'B', 123])
    'a=%E4%B8%AD%E6%96%87&b=A&b=B&b=123'
    '''
    args = []
    for k, v in kw.iteritems():
        if isinstance(v, basestring):
            qv = v.encode('utf-8') if isinstance(v, unicode) else v
            args.append('%s=%s' % (k, urllib.quote(qv)))
        elif isinstance(v, collections.Iterable):
            for i in v:
                qv = i.encode('utf-8') if isinstance(i, unicode) else str(i)
                args.append('%s=%s' % (k, urllib.quote(qv)))
        else:
            qv = str(v)
            args.append('%s=%s' % (k, urllib.quote(qv)))
    return '&'.join(args)

def _read_body(obj):
    using_gzip = obj.headers.get('Content-Encoding', '')=='gzip'
    body = obj.read()
    if using_gzip:
        gzipper = gzip.GzipFile(fileobj=StringIO(body))
        fcontent = gzipper.read()
        gzipper.close()
        return fcontent
    return body

#!/usr/bin/env python
#coding=utf-8

import ujson as json
import redis
import config
import murmur
import tldextracter

POOL = redis.ConnectionPool(host=config.RHOST,
                            port=config.RPORT,
                            db=config.RDB)


def check_fetched(url):
    r = redis.Redis(connection_pool=POOL)
    mhash = murmur.string_hash(url)
    if r.getbit(config.BITMAP, mhash):
        return True
    else:
        r.setbit(config.BITMAP, mhash, 1)
        return False


def filter_recent(r, jobs):
    filtered_jobs = []
    for job in jobs:
        try:
            task = json.loads(job)
            url = task['url']
            del task
            rootdomain = tldextracter.extract_rootdomain(url)
        except:
            r.lpush(config.QUEUE, job)

        try:
            if not r.exists('%s_status' % rootdomain):
                r.set('%s_status' % rootdomain, '')
                r.expire('%s_status' % rootdomain, config.EXPIRE)
                filtered_jobs.append(job)
            else:
                r.lpush(config.QUEUE, job)
        except Exception, e:
            print e
            return jobs
    return filtered_jobs


def get_jobs(limit=100):
    r = redis.Redis(connection_pool=POOL)
    queues = r.keys(config.QUEUE_FORMAT % '*')
    jobs = []
    for i in xrange(config.POP_TIMES):
        jobs = jobs + [r.rpop(queue) for queue in queues]
    not_null_jobs = filter(None, jobs)
    filtered_jobs = filter_recent(r, not_null_jobs)
    return filtered_jobs


def get_queue(limit=100):
    r = redis.Redis(connection_pool=POOL)
    jobs = [r.rpop(config.QUEUE) for i in xrange(0, limit)]
    not_null_jobs = filter(None, jobs)
    filtered_jobs = filter_recent(r, not_null_jobs)
    return filtered_jobs


def push(url, detail=True):

    if isinstance(url, unicode):
        try:
            url = url.strip().encode('utf8')
        except Exception, e:
            print e
            pass
    rootdomain = tldextracter.extract_rootdomain(url)
    if not rootdomain:
        return False
    if check_fetched(url):
        return False
    r = redis.Redis(connection_pool=POOL)
    job = {'url': url}
    if detail:
        r.rpush(config.QUEUE_FORMAT % rootdomain, json.dumps(job))
    else:
        r.lpush(config.QUEUE_FORMAT % rootdomain, json.dumps(job))
    del job
    return True


def qpush(url, detail=True):

    if isinstance(url, unicode):
        try:
            url = url.strip().encode('utf8')
        except Exception, e:
            print e
            pass
    #todo urlnorm
    rootdomain = tldextracter.extract_rootdomain(url)
    if not rootdomain:
        return False
    if check_fetched(url):
        return False
    r = redis.Redis(connection_pool=POOL)
    job = {'url': url}
    if detail:
        r.rpush(config.QUEUE, json.dumps(job))
    else:
        r.lpush(config.QUEUE, json.dumps(job))
    del job
    return True


def get_expire_proxy():
    r = redis.Redis(connection_pool=POOL)
    proxy = r.srandmember('proxies')
    while r.exists('proxy_%s' % proxy):
        proxy = r.srandmember('proxies')
    r.expire('proxy_%s' % proxy, config.PROXY_EXPIRETIME)
    return proxy


def get_random_proxy():
    r = redis.Redis(connection_pool=POOL)
    proxy = r.srandmember('proxies')
    return proxy


def get_proxy():
    r = redis.Redis(connection_pool=POOL)
    proxy = r.get('proxy')
    return proxy


def get_random_useragent():
    r = redis.Redis(connection_pool=POOL)
    useragent = r.srandmember('useragents')
    return useragent


if __name__ == '__main__':
    from rulers import RULERS
    urls = [RULERS[domain]["url"] for domain in RULERS]
    map(qpush, urls)

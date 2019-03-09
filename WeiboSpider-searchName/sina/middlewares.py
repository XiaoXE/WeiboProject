# encoding: utf-8
import random
import requests
import pickle
import pymongo
from sina.settings import LOCAL_MONGO_PORT, LOCAL_MONGO_HOST, DB_NAME


class CookieMiddleware(object):
    """
    每次请求都随机从账号池中选择一个账号去访问
    """

    def __init__(self):
        client = pymongo.MongoClient(LOCAL_MONGO_HOST, LOCAL_MONGO_PORT)
        self.account_collection = client[DB_NAME]['account']

    def process_request(self, request, spider):
        all_count = self.account_collection.find({'status': 'success'}).count()
        if all_count == 0:
            raise Exception('当前账号池为空')
        random_index = random.randint(0, all_count - 1)
        random_account = self.account_collection.find({'status': 'success'})[random_index]
        request.headers.setdefault('Cookie', random_account['cookie'])
        request.meta['account'] = random_account
#添加我自己的代理设置类,执行顺序在CookieMiddleware和RedirectMiddleware之间
PROXY_FILE = r'E:\FDSM_HeXiao\WeiboSpider-search\myproxies.pkl'
class RandomProxyMiddleware(object):
    """
    从pkl文件中读取有效的ip地址，进行有效应验证，动态获取ip代理
    """
    def test_ip(self,proxy):
        try:
            requests.get('https://weibo.cn/', proxies=proxy)
        except:
            print('ipproxy failed')
            return False
        else:
            print('proxy success')
            return True

    def process_request(self, request, spider):
        #proxy_ip = requests.get(PROXY_POOL_URL).text
        proxy_flag = False
        with open(PROXY_FILE,'rb') as f:
            proxy_ips = pickle.load(f)
        proxy_ip = random.choice(proxy_ips)
        print('the current proxy is',proxy_ip)
        request.meta["proxy"] = proxy_ip

class RedirectMiddleware(object):
    """
    检测账号是否正常
    302 / 403,说明账号cookie失效/账号被封，状态标记为error
    418,偶尔产生,需要再次请求
    """

    def __init__(self):
        client = pymongo.MongoClient(LOCAL_MONGO_HOST, LOCAL_MONGO_PORT)
        self.account_collection = client[DB_NAME]['account']

    def process_response(self, request, response, spider):
        http_code = response.status
        if http_code == 302 or http_code == 403:
            self.account_collection.find_one_and_update({'_id': request.meta['account']['_id']},
                                                        {'$set': {'status': 'error'}}, )
            return request
        elif http_code == 418:
            spider.logger.error('ip 被封了!!!请更换ip,或者停止程序...')
            return request
        else:
            return response

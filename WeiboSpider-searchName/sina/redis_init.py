#!/usr/bin/env python
# encoding: utf-8
import redis
import sys
import os
import time
import datetime
import pymongo
sys.path.append(os.getcwd())
from sina.settings import LOCAL_MONGO_HOST, LOCAL_MONGO_PORT, DB_NAME
from sina.settings import LOCAL_REDIS_HOST, LOCAL_REDIS_PORT

r = redis.Redis(host=LOCAL_REDIS_HOST, port=LOCAL_REDIS_PORT)
for key in r.scan_iter("weibo_spider*"):
    r.delete(key)
    print('Sucess Deleted!!!')
# 可以修改，对某天之后爬到的昵称进行爬取；输入日期，直接转化成当日0点的timestamp
db_start_crawl_time = time.mktime(datetime.datetime.strptime("2019-03-08", '%Y-%m-%d').timetuple())
def get_names_from_mongo(db_start_time):
    """
    根据时间从mongodb中取出需要的昵称
    :param db_start_time:
    :return:
    """
    # TODO
    client = pymongo.MongoClient(LOCAL_MONGO_HOST, LOCAL_MONGO_PORT)
    db = client[DB_NAME]
    info_collection = db["Tweets"]
    print(info_collection,db_start_time)
    names_result = info_collection.find({'crawl_time': {'$gt': db_start_time}})
    # for i in names_result:
    #     print(i['asker_name'])
    return names_result  # 返回的是一个generator
# TODO 修改为找人
# 搜索的关键词，可以修改
# url_format = "https://weibo.cn/search/mblog?hideSearchFrame=&keyword={}&advancedfilter=1&hasori=1&hasv=1&starttime={}&endtime={}&sort=time&page=1"
# https://weibo.cn/search/mblog/?keyword=&advanced=mblog&rl=0&f=s
for name in get_names_from_mongo(db_start_crawl_time):
    # referer: https://weibo.cn/search/user/?keyword=&advanced=user&rl=0&f=s
    # advancedfilter=1&keyword=Yz_W%E5%93%B2&type=nick&isv=all&gender=all&age=0&suser=%E6%90%9C%E7%B4%A2
    # print(name['asker_name'])
    url = f"https://weibo.cn/search/user?advancedfilter=1&keyword={name['asker_name']}&type=nick&isv=all&gender=all&age=0&suser=%E6%90%9C%E7%B4%A2"
    r.lpush('weibo_spider:start_urls', url)
    print('添加{}成功'.format(url))


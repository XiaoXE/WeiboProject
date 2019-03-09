#!/usr/bin/env python
# encoding: utf-8
import redis
import sys
import os
import datetime
sys.path.append(os.getcwd())
from sina.settings import LOCAL_REDIS_HOST, LOCAL_REDIS_PORT

r = redis.Redis(host=LOCAL_REDIS_HOST, port=LOCAL_REDIS_PORT)
for key in r.scan_iter("weibo_spider*"):
    r.delete(key)
    print('Sucess Deleted!!!')

# url_format = "https://weibo.cn/search/mblog?hideSearchFrame=&keyword={}&advancedfilter=1&starttime={}&endtime={}&sort=time&page=1"
# # 搜索的关键词，可以修改
# keyword = "转基因"
# # 搜索的起始日期，可修改 微博的创建日期是2009-08-16 也就是说不要采用这个日期更前面的日期了
# date_start = datetime.datetime.strptime("2017-07-30", '%Y-%m-%d')
# # 搜索的结束日期，可修改
# date_end = datetime.datetime.strptime("2018-07-30", '%Y-%m-%d')
url_format = "https://weibo.cn/search/mblog?hideSearchFrame=&keyword={}&advancedfilter=1&hasori=1&hasv=1&starttime={}&endtime={}&sort=time&page=1"
# 搜索的关键词，可以修改
keyword = "大家快来花1元围观～"
# 搜索的起始日期，可修改 微博的创建日期是2009-08-16 也就是说不要采用这个日期更前面的日期了
date_start = datetime.datetime.strptime("2018-12-01", '%Y-%m-%d')
# 搜索的结束日期，可修改
date_end = datetime.datetime.strptime("2019-03-08", '%Y-%m-%d')
time_spread = datetime.timedelta(days=1)
while date_start < date_end:
    next_time = date_start + time_spread
    url = url_format.format(keyword, date_start.strftime("%Y%m%d"), next_time.strftime("%Y%m%d"))
    r.lpush('weibo_spider:start_urls', url)
    date_start = next_time
    print('添加{}成功'.format(url))

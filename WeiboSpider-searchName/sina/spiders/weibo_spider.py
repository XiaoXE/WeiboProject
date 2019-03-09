#!/usr/bin/env python
# encoding: utf-8
import re
from lxml import etree
from scrapy.crawler import CrawlerProcess
from scrapy.selector import Selector
from scrapy.http import Request
from scrapy.utils.project import get_project_settings
from scrapy_redis.spiders import RedisSpider
from sina.items import InformationItem
from sina.spiders.utils import time_fix
import time

# TODO 获取提问人的信息 done

class WeiboSpider(RedisSpider):
    name = "weibo_spider2"
    base_url = "https://weibo.cn"
    redis_key = "weibo_spider:start_urls"

    custom_settings = {
        'CONCURRENT_REQUESTS': 13,
        "DOWNLOAD_DELAY": 0.2,
        'RETRY_TIMES': 40
    }

    def parse(self, response):
        """
        解析搜索页面
        :param response:
        :return:
        """
        if response.url.endswith('page=1'):
            # 如果是第1页，一次性获取后面的所有页
            all_page = re.search(r'/>&nbsp;1/(\d+)页</div>', response.text)
            if all_page:
                all_page = all_page.group(1)
                all_page = int(all_page)
                for page_num in range(2, all_page + 1):
                    page_url = response.url.replace('page=1', 'page={}'.format(page_num))
                    yield Request(page_url, self.parse, dont_filter=True, meta=response.meta)
        """
        解析本页的数据
        """
        # print(response)
        tree_node = etree.HTML(response.body)
        # TODO 程序反应[0]有错误，out of index boundary,问题不大，因为实在没找到这个人的情况下
        user_node = tree_node.xpath('//tr')[0] # 选择第一个结果
        #for user_node in tweet_nodes:
        if user_node:
            try:
                #tweet_item['crawl_time'] = int(time.time())
                user_url = user_node.xpath('.//a/@href')[0]
                # <a href="/u/1700338344?f=search_0">
                user_tweet_id = re.search(r'/u/(\d*?)\?f', user_url).group(1)
                # tweet_item['user_id'] = user_tweet_id.group(1)
                # tweet_item['id'] = '{}_{}'.format(user_tweet_id.group(2), user_tweet_id.group(1))
                yield Request(url="https://weibo.cn/{}/info".format(user_tweet_id),
                              callback=self.parse_information)
            except Exception as e:
                self.logger.error(e)

    # 默认初始解析函数
    def parse_information(self, response):
        """

        :param response:
        :param from_twitter_id: 用来获取asker的爬取来自哪一个twitter，但是好像没有必要，因为数据都是当天爬取的
        :return:
        """
        """ 抓取个人信息 """
        information_item = InformationItem()
        information_item['crawl_time'] = int(time.time())
        selector = Selector(response)
        information_item['id'] = re.findall('(\d+)/info', response.url)[0]
        text1 = ";".join(selector.xpath('body/div[@class="c"]//text()').extract())  # 获取标签里的所有text()
        nick_name = re.findall('昵称;?[：:]?(.*?);', text1)
        gender = re.findall('性别;?[：:]?(.*?);', text1)
        place = re.findall('地区;?[：:]?(.*?);', text1)
        brief_introduction = re.findall('简介;[：:]?(.*?);', text1)
        birthday = re.findall('生日;?[：:]?(.*?);', text1)
        sex_orientation = re.findall('性取向;?[：:]?(.*?);', text1)
        sentiment = re.findall('感情状况;?[：:]?(.*?);', text1)
        vip_level = re.findall('会员等级;?[：:]?(.*?);', text1)
        authentication = re.findall('认证;?[：:]?(.*?);', text1)
        if nick_name and nick_name[0]:
            information_item["nick_name"] = nick_name[0].replace(u"\xa0", "")
        if gender and gender[0]:
            information_item["gender"] = gender[0].replace(u"\xa0", "")
        if place and place[0]:
            place = place[0].replace(u"\xa0", "").split(" ")
            information_item["province"] = place[0]
            if len(place) > 1:
                information_item["city"] = place[1]
        if brief_introduction and brief_introduction[0]:
            information_item["brief_introduction"] = brief_introduction[0].replace(u"\xa0", "")
        if birthday and birthday[0]:
            information_item['birthday'] = birthday[0]
        if sex_orientation and sex_orientation[0]:
            if sex_orientation[0].replace(u"\xa0", "") == gender[0]:
                information_item["sex_orientation"] = "同性恋"
            else:
                information_item["sex_orientation"] = "异性恋"
        if sentiment and sentiment[0]:
            information_item["sentiment"] = sentiment[0].replace(u"\xa0", "")
        if vip_level and vip_level[0]:
            information_item["vip_level"] = vip_level[0].replace(u"\xa0", "")
        if authentication and authentication[0]:
            information_item["authentication"] = authentication[0].replace(u"\xa0", "")
        request_meta = response.meta
        request_meta['item'] = information_item
        yield Request(self.base_url + '/u/{}'.format(information_item['id']),
                      callback=self.parse_further_information,
                      meta=request_meta, dont_filter=True, priority=4)

    def parse_further_information(self, response):
        text = response.text
        information_item = response.meta['item']
        tweets_num = re.findall('微博\[(\d+)\]', text)
        if tweets_num:
            information_item['tweets_num'] = int(tweets_num[0])
        follows_num = re.findall('关注\[(\d+)\]', text)
        if follows_num:
            information_item['follows_num'] = int(follows_num[0])
        fans_num = re.findall('粉丝\[(\d+)\]', text)
        if fans_num:
            information_item['fans_num'] = int(fans_num[0])
        yield information_item


if __name__ == "__main__":
    process = CrawlerProcess(get_project_settings())
    process.crawl('weibo_spider2')
    process.start()

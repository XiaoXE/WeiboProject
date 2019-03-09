#!/usr/bin/env python
# encoding: utf-8
import re
from lxml import etree
from scrapy.crawler import CrawlerProcess
from scrapy.selector import Selector
from scrapy.http import Request
from scrapy.utils.project import get_project_settings
from scrapy_redis.spiders import RedisSpider
from sina.items import TweetsItem, InformationItem, CommentItem
from sina.spiders.utils import time_fix
import time

# TODO 获取提问人的信息 done
# TODO 获取微博的评论信息 done
# TODO 人的社交关系不能获取， 每个微博都会涉及到两个人，效率很低 done
"""
num 越小越先被执行
priority 1: Request(all_content_url, callback=self.parse_all_content, meta={'item': tweet_item},
                                  priority=1)
priority 2 : Request(url="https://weibo.cn/{}/info".format(tweet_item['user_id']),
                              callback=self.parse_information, priority=2, meta={'is_asker': 0})
priority 2 -> 3:Request(url=asker_name_url, callback=self.parse_information, meta={'is_asker':1}, priority=3)
priority 4: Request(self.base_url + '/u/{}'.format(information_item['_id']),
                      callback=self.parse_further_information,
                      meta=request_meta, dont_filter=True, priority=4)
priority 5:Request(url=comment_url, callback=self.parse_comment,
                                  meta={'weibo_url': tweet_item['weibo_url']}, priority=5)
"""

class WeiboSpider(RedisSpider):
    name = "weibo_spider"
    base_url = "https://weibo.cn"
    redis_key = "weibo_spider:start_urls"

    custom_settings = {
        'CONCURRENT_REQUESTS': 16,
        "DOWNLOAD_DELAY": 0.3,
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
        tree_node = etree.HTML(response.body)
        tweet_nodes = tree_node.xpath('//div[@class="c" and @id]')
        for tweet_node in tweet_nodes:
            try:
                tweet_item = TweetsItem()
                tweet_item['crawl_time'] = int(time.time())
                tweet_repost_url = tweet_node.xpath('.//a[contains(text(),"转发[")]/@href')[0]
                user_tweet_id = re.search(r'/repost/(.*?)\?uid=(\d+)', tweet_repost_url)
                tweet_item['weibo_url'] = 'https://weibo.com/{}/{}'.format(user_tweet_id.group(2),
                                                                           user_tweet_id.group(1))
                tweet_item['user_id'] = user_tweet_id.group(2)
                tweet_item['_id'] = '{}_{}'.format(user_tweet_id.group(2), user_tweet_id.group(1))
                create_time_info = tweet_node.xpath('.//span[@class="ct"]/text()')[-1]
                if "来自" in create_time_info:
                    tweet_item['created_at'] = time_fix(create_time_info.split('来自')[0].strip())
                else:
                    tweet_item['created_at'] = time_fix(create_time_info.strip())

                like_num = tweet_node.xpath('.//a[contains(text(),"赞[")]/text()')[-1]
                tweet_item['like_num'] = int(re.search('\d+', like_num).group())

                repost_num = tweet_node.xpath('.//a[contains(text(),"转发[")]/text()')[-1]
                tweet_item['repost_num'] = int(re.search('\d+', repost_num).group())
                comment_num = tweet_node.xpath(
                    './/a[contains(text(),"评论[") and not(contains(text(),"原文"))]/text()')[-1]
                tweet_item['comment_num'] = int(re.search('\d+', comment_num).group())
                tweet_content_node = tweet_node.xpath('.//span[@class="ctt"]')[0]

                # TODO 这里加上获取提问者的user_id的解析
                # 换一下顺序，放到回答者的request后面，不行，这里的asker_name_url并不包含info
                # 通过xpath结合正则表达式提取提问者的user_id，或者直接就是他的个人页面,但是这里获得的是以昵称为url的，跳转之后返回的就是id了
                asker_name_url = tweet_node.xpath('.//a[contains(text(),"@")]/text()')[0]
                tweet_item['asker_name'] = asker_name_url.split('@')[-1]
                print('提问者的url', tweet_item['asker_name'])
                # TODO 这里yield一个提问者的request
                # https://blog.csdn.net/rgc_520_zyl/article/details/78946974
                #header = {,'User-Agent': 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.109 Safari/537.36'}
                #yield Request(url=asker_name_url, callback=self.parse_asker, priority=1, meta={'asker_from': tweet_item['weibo_url']})

                # 检测由没有阅读全文:
                all_content_link = tweet_content_node.xpath('.//a[text()="全文"]')
                if all_content_link:
                    all_content_url = self.base_url + all_content_link[0].xpath('./@href')[0]
                    yield Request(all_content_url, callback=self.parse_all_content, meta={'item': tweet_item},
                                  priority=1)

                else:
                    all_content = tweet_content_node.xpath('string(.)').replace('\u200b', '').strip()
                    tweet_item['content'] = all_content[1:]
                    yield tweet_item

                # yield Request(url="https://weibo.cn/{}/info".format(tweet_item['user_id']),
                #               callback=self.parse_information, priority=2)
                yield Request(url="https://weibo.cn/{}/info".format(tweet_item['user_id']),
                              callback=self.parse_information, priority=2)

                # TODO 检测有无评论，如果有yield一个parse_comment
                if tweet_item['comment_num'] > 0:
                    # 抓取该微博的评论信息
                    comment_url = self.base_url + '/comment/' + tweet_item['weibo_url'].split('/')[-1] + '?page=1'
                    yield Request(url=comment_url, callback=self.parse_comment,
                                  meta={'weibo_url': tweet_item['weibo_url']}, priority=5)

            except Exception as e:
                self.logger.error(e)

    def parse_comment(self, response):
        # 如果是第1页，一次性获取后面的所有页
        if response.url.endswith('page=1'):
            all_page = re.search(r'/>&nbsp;1/(\d+)页</div>', response.text)
            if all_page:
                all_page = all_page.group(1)
                all_page = int(all_page)
                for page_num in range(2, all_page + 1):
                    page_url = response.url.replace('page=1', 'page={}'.format(page_num))
                    yield Request(page_url, self.parse_comment, dont_filter=True, meta=response.meta)
        selector = Selector(response)
        comment_nodes = selector.xpath('//div[@class="c" and contains(@id,"C_")]')
        for comment_node in comment_nodes:
            comment_user_url = comment_node.xpath('.//a[contains(@href,"/u/")]/@href').extract_first()
            if not comment_user_url:
                continue
            comment_item = CommentItem()
            comment_item['crawl_time'] = int(time.time())
            comment_item['weibo_url'] = response.meta['weibo_url']
            comment_item['comment_user_id'] = re.search(r'/u/(\d+)', comment_user_url).group(1)
            comment_item['content'] = comment_node.xpath('.//span[@class="ctt"]').xpath('string(.)').extract_first()
            comment_item['_id'] = comment_node.xpath('./@id').extract_first()
            created_at = comment_node.xpath('.//span[@class="ct"]/text()').extract_first()
            comment_item['created_at'] = time_fix(created_at.split('\xa0')[0])
            yield comment_item


    def parse_all_content(self, response):
        # 有阅读全文的情况，获取全文
        tree_node = etree.HTML(response.body)
        tweet_item = response.meta['item']
        content_node = tree_node.xpath('//div[@id="M_"]//span[@class="ctt"]')[0]
        all_content = content_node.xpath('string(.)').replace('\u200b', '').strip()
        tweet_item['content'] = all_content[1:]
        yield tweet_item
    def parse_asker(self, response):
        """
        这是专门对asker进行解析的方法，
        :param response:
        :return:
        """
        asker_from_url = response.meta['asker_from']
        asker_url = response.url
        asker_id = asker_url.split('/')[-1]
        print("ASKER ID IS ", asker_id)
        yield Request(url=f"https://weibo.cn/{asker_id}/info",
                      callback=self.parse_information, priority=2, meta={'asker_from': asker_from_url})
    # 默认初始解析函数
    def parse_information(self, response):
        """

        :param response:
        :param from_twitter_id: 用来获取asker的爬取来自哪一个twitter，但是好像没有必要，因为数据都是当天爬取的
        :return:
        """
        """ 抓取个人信息 """
        information_item = InformationItem()
        # if 'asker_from' in response.meta:
        #     information_item['asker_from_url'] = response.meta['asker_from']
        information_item['crawl_time'] = int(time.time())
        selector = Selector(response)
        information_item['_id'] = re.findall('(\d+)/info', response.url)[0]
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
        yield Request(self.base_url + '/u/{}'.format(information_item['_id']),
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
    process.crawl('weibo_spider')
    process.start()

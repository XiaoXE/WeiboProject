import pickle
import os
import time
import sys
sys.path.append(r'E:\FDSM_HeXiao\haipproxy-0.1')
from client.py_cli import ProxyFetcher

def print_ts(message):
    print("[%s] %s"%(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()), message))
def run(interval, command):
    print_ts("-"*100)
    #print_ts("Command %s"%command)
    print_ts("Starting every %s seconds."%interval)
    print_ts("-"*100)
    while True:
        try:
            # sleep for the remaining seconds of interval
            time_remaining = interval-time.time()%interval
            print_ts("Sleeping until %s (%s seconds)..."%((time.ctime(time.time()+time_remaining)), time_remaining))
            time.sleep(time_remaining)
            print_ts("Starting command.")
            # execute the command
            args = dict(host='127.0.0.1', port=6379, password='', db=0)
            fetcher = ProxyFetcher('weibo', strategy='greedy', redis_args=args)
            myproxy = fetcher.get_proxies()
            print(myproxy)
            with open(r'E:\FDSM_HeXiao\WeiboSpider-search\myproxies.pkl', 'wb') as f:
                pickle.dump(myproxy, f)
            print_ts("-"*100)
        except Exception as e:
            print(e)
if __name__=="__main__":
    interval = 5*60
    command = r"ls"
    run(interval, command)
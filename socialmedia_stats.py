import requests
from TwitterSearch import TwitterSearch
from TwitterSearch import TwitterSearchOrder

# functions that return like/share counts from social media posts that contain a specified url in them

class Stat:
    def getStats(self):
        return 0

class FacebookStat(Stat):
    def __init__(self):
        pass

    def getStats(self, url, proxy, headers, timeout):
        """returns (share + comment) count from facebook API, url is url that is mentioned in a facebook post and is string, proxy is 'ip:port' in string, headers should contain user-agent in as an item in dictionary, timeout is maximum time while waiting for response and is an int"""
        response = requests.get('https://graph.facebook.com/?fields=share&id=' + url,
                                proxies={'http': 'http://%s' % proxy}, headers=headers, timeout=timeout)

        if response.status_code != 200:
            raise Exception('Facebook graph api query, invalid response, status_code = ' + str(response.status_code))

        JsonObj = response.json()
        count = JsonObj['share']['comment_count'] + JsonObj['share']['share_count']
        return count

class TwitterStat(Stat):
    def __init__(self):
        self.ConsumerKey = ''
        self.AccessTokenKey = ''
        self.ConsumerSecret = ''
        self.AccessTokenSecret = ''

    def getStats(self, url, proxy, headers, timeout):
        """returns (retweet + favorite count) count from twitter API , url is url that could be in a tweet, proxy is 'ip:port' in string, headers should contain user-agent in as an item in dictionary, timeout is maximum time while waiting for response and is an int"""
        count = 0

        tso = TwitterSearchOrder()
        tso.set_search_url('q=' + url)
        tso.set_result_type(result_type='mixed')
        tso.set_include_entities(False)
        tso.set_count(100)

        ts = TwitterSearch(consumer_key=self.ConsumerKey, consumer_secret=self.ConsumerSecret,
                           access_token=self.AccessTokenKey, access_token_secret=self.AccessTokenSecret,
                           proxy=proxy)

        for tweet in ts.search_tweets_iterable(tso):
            count += tweet['retweet_count'] + tweet['favorite_count']

        return count
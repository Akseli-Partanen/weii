# coding=utf-8

from PyQt4.QtCore import *
from PyQt4.QtGui import *

from app.widget.ContentWidget import abstract_widget
from app import logger

log = logger.getLogger(__name__)

class TweetData():
    def __init__(self, account, tweet_list, picture_list):
        self.account = account
        self.tweet_list = tweet_list
        self.picture_list = picture_list

class HomeWidget(abstract_widget.AbstractTweetContainer):
    '''
    Home tab
    '''
    def retrieveData(self, account_list, page=1, count=20):
        rtn = []
        for account in account_list:
            #log.debug(account.plugin)
            tweet_list = account.plugin.getTimeline(max_point=(account.last_tweet_id, account.last_tweet_time),
                page=page, count=count
            )
            for tweet in tweet_list:
                tweet['type'] = abstract_widget.TWEET
            rtn.append((account, tweet_list))
            
        log.debug('Download finished')
        return (rtn, ), {}

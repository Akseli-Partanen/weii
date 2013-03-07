# coding=utf-8

import json
import imghdr
from PyQt4.QtCore import *
from PyQt4.QtGui import *

from widget.ContentWidget import abstract_widget
from widget.tweet_widget import TweetWidget
from app import constant
from app import logger

log = logger.getLogger(__name__)
SIGNAL_FINISH = 'downloadFinish'

class TweetData():
    def __init__(self, account, tweet_list, picture_list):
        self.account = account
        self.tweet_list = tweet_list
        self.picture_list = picture_list

class DownloadTask(QThread):
    def __init__(self):
        #super(DownloadTask, self).__init__(self)
        QThread.__init__(self)
        
    def setAccountList(self, account_list):
        self.account_list = account_list
        
    def run(self):
        data_list = []
        
        for account in self.account_list:
            tweet_list = account.plugin.getTimeline()
            picture_list = []
            
            for tweet in tweet_list:
                if 'thumbnail_pic' in tweet:
                    picture = True
                elif ('retweeted_status' in tweet) and ('thumbnail_pic' in tweet['retweeted_status']):
                    picture = True
                else:
                    picture = False
                picture_list.append(picture)
                
            data_list.append(
                TweetData(account, tweet_list, picture_list)
            )
            
        log.debug('Download finished')
        self.emit(SIGNAL(SIGNAL_FINISH), data_list)

class HomeWidget(abstract_widget.AbstractWidget):
    '''
    Home tab
    '''
    
    def __init__(self, theme, parent=None):
        super(HomeWidget, self).__init__(theme, parent)
        self.download_task = DownloadTask()
        self.loading_image = QMovie(theme.skin['loading-image'])
        self.loading_image.start()
        
        self.small_loading_image = QMovie(theme.skin['loading-image'])
        self.small_loading_image.setScaledSize(QSize(constant.AVATER_IN_TWEET_SIZE, constant.AVATER_IN_TWEET_SIZE))
        self.small_loading_image.start()
        
        self.connect(self.download_task, SIGNAL(SIGNAL_FINISH), self.updateUI)
        
        # debug
        self.tweets = (tweet for tweet in json.load(open('json'))['statuses']) 
        
    def updateUI(self, data_list):
        log.debug('updateUI')
        for tweet_data in data_list:
            length = len(tweet_data.tweet_list)
            i = 0
            while(i < length):
                avatar = self.small_loading_image
                
                has_picture = tweet_data.picture_list[i]
                if has_picture:
                    picture = self.loading_image
                else:
                    picture = None
                    
                self.addWidget(
                    TweetWidget(tweet_data.account, tweet_data.tweet_list[i], avatar, picture, self)
                )
                i += 1
        
    def refresh(self, account_list):
        if not self.download_task.isRunning():
            self.download_task.setAccountList(account_list)
            log.debug('Starting thread')
            self.download_task.start()
            
#    def refresh(self, account_list):
#        self.clearWidget()
#        tweets = json.load(open('json'))['statuses']
#        for tweet in tweets:
#            widget = TweetWidget(account_list[0], tweet, self.small_loading_image, self.loading_image, self)
#            self.addWidget(widget)
#        pass
    
#    def refresh(self, account_list):
#        self.addWidget(TweetWidget(None, next(self.tweets), self.avatar.scaled(constant.AVATER_IN_TWEET_SIZE, constant.AVATER_IN_TWEET_SIZE), None, self))

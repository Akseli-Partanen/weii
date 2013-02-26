# coding=utf-8

import time
import random
import json
from PyQt4.QtCore import *
from PyQt4.QtGui import *

from widget.ContentWidget import AbstractWidget
from widget.TweetWidget import TweetWidget
from app import constant


class HomeWidget(AbstractWidget.AbstractWidget):
    '''
    Home tab
    '''
    
    def __init__(self, parent=None):
        super(HomeWidget, self).__init__(parent)
        self.service_icon = QPixmap(constant.TEST_SERVICE)
        self.avater = QPixmap(constant.DEFAULT_AVATER)
        
        # debug
        self.tweets = (tweet for tweet in json.load(open('json'))['statuses']) 
        
#    def refresh(self, account_list):
#        for account in account_list:
#            timeline = account.plugin.getTimeline()
#            for tweet in timeline:
#                self.addWidget(TweetWidget(
#                    account, tweet, account.service_icon, self.avater.scaled(40, 40), None, self))
            
    def refresh(self, account_list):
        tweets = json.load(open('json'))['statuses']
        for tweet in tweets:
            self.addWidget(TweetWidget(None, tweet, self.service_icon, self.avater.scaled(40, 40), None, self))
            #self.insertWidget(0, QLabel(str(i)))
        pass
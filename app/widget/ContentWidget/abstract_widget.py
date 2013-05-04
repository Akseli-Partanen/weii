# coding=utf-8

import time
import json

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from app import account_manager
from app import easy_thread
from app import constant
from app import theme_manager
from app import logger
from app import dateutil
from app import keywords
from app.dateutil import parser
from app.widget.tweet_widget import TweetWidget

log = logger.getLogger(__name__)

######################################################################
# Tweet type. The alternative value of key 'type' in Tweet object.
COMMENT = 0
TWEET = 1
######################################################################

class AbstractWidget(QWidget):
    '''
    Abstract widget for holding content
    '''
    
    def __init__(self, parent=None):
        super(AbstractWidget, self).__init__(parent)
        self.theme_manager= theme_manager.getCurrentTheme()
        
        self.loading_image = QMovie(theme_manager.getParameter('Skin', 'loading-image'))
        self.loading_image.start()
        
        self.small_loading_image = QMovie(theme_manager.getParameter('Skin', 'loading-image'))
        self.small_loading_image.setScaledSize(QSize(constant.AVATER_IN_TWEET_SIZE, constant.AVATER_IN_TWEET_SIZE))
        self.small_loading_image.start()
        
        image = QMovie(theme_manager.getParameter('Skin', 'loading-image'))
        image.setScaledSize(QSize(32, 32))
        image.start()
        self.retrievingData_image = QLabel()
        self.retrievingData_image.setMovie(image)
        self.retrievingData_image.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
#        self.retrievingData_image.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
#        self.retrievingData_image.setFixedSize(32, 32)
        self.setupUI()
        
        
    def setupUI(self):
        frame_layout = QVBoxLayout()
        frame_layout.setMargin(0)
        self.__layout = QVBoxLayout()
        self.__layout.setMargin(0)
        self.__layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        frame_layout.addLayout(self.__layout)
        frame_layout.addStretch()
        self.setLayout(frame_layout)
        
    def count(self):
        return self.__layout.count()
        
    def clearWidget(self, widget):
        widget.hide()
        self.__layout.removeWidget(widget)
        
    def clearAllWidgets(self):
        while(True):
            child = self.__layout.itemAt(0)
            if child:
                self.clearWidget(child.widget())
                del child
            else:
                break
        
    def itemAt(self, index):
        return self.__layout.itemAt(index)
        
    def insertWidget(self, pos, widget):
        '''
        @param pos: Insert at pos
        @param widget: Widget to be added
        '''
        self.__layout.insertWidget(pos, widget)
        
    def addWidget(self, widget):
        '''
        @param widget: Widget to be added
        '''
        self.__layout.addWidget(widget)
    
    def refresh(self):
        '''
        Refresh self with data from account list
        @param account_list: List of account objects(Plugin)
        '''
        raise NotImplementedError

class AbstractTweetContainer(AbstractWidget):
    def __init__(self, parent=None):
        super(AbstractTweetContainer, self).__init__(parent)
        self.currentPage = 1
        self.time_format = '%a %b %d %H:%M:%S %z %Y'
        self.retrievingData = False
        self.refreshing = False
        
    def produceWidget(self, account, tweet, avatar, picutre):
        '''
        Abstract method to produce widget
        @param account: account_manager.Account object
        @param tweet: Tweet object
        @param avatar: QMovie. Loading image. gif
        @param picture: QMovie. Loading image. gif
        '''
        if keywords.checkForJunk(tweet['text']):
            return None
        elif ('retweeted_status') in tweet and keywords.checkForJunk(tweet['retweeted_status']['text']):
            return None
        else:
            return TweetWidget(account, tweet, avatar, picutre, self)
    
    def retrieveData(self, account_list, page=1, count=20):
        raise NotImplementedError
        
    def updateUI(self, data):
        log.debug('updateUI')
        self.clearWidget(self.retrievingData_image)
        whole_list = []
        for account,tweet_list in data:
            # If it is refreshing(only retrievingData_image exists), update max_point of account
            if self.refreshing:
                account.last_tweet_id = tweet_list[0]['id']
                account.last_tweet_time = tweet_list[0]['created_at']
                self.clearAllWidgets()
                self.refreshing = False
                
            if isinstance(tweet_list, dict):
                QMessageBox.critical(None, account.plugin.service, tweet_list['error'])
                continue
                
            for tweet in tweet_list:
                created_at = tweet['created_at']
                if created_at:
                    dt = parser.parse(created_at)
                    res = dt.astimezone(dateutil.tz.tzlocal())
                    tweet['created_at'] = time.mktime(res.timetuple())
                
                if 'retweeted_status' in tweet:
                    retweet = tweet['retweeted_status']
                    created_at = retweet['created_at']
                    if created_at:
                        dt = parser.parse(retweet['created_at'])
                        res = dt.astimezone(dateutil.tz.tzlocal())
                        retweet['created_at'] = time.mktime(res.timetuple())
                whole_list.append((account, tweet))
        
        whole_list.sort(key=lambda x:x[1]['created_at'], reverse=True)
                
        for account, tweet in whole_list:
            avatar = self.small_loading_image
            picture = self.loading_image
                
            widget = self.produceWidget(account, tweet, avatar, picture)
            if widget:
                # Not junk ads
                self.addWidget(widget)
        self.retrievingData = False
        
    def appendNew(self):
        if self.retrievingData:
            return
        
        account_list = account_manager.getCurrentAccount()
        
        self.retrievingData_image.show()
        self.insertWidget(-1, self.retrievingData_image)
        
        self.retrievingData = True
        easy_thread.start(self.retrieveData, args=(account_list, self.currentPage, 20), callback=self.updateUI)
        log.debug('Starting thread')
        self.currentPage += 1
        
#    def refresh(self):
#        if self.retrievingData:
#            return
#        else:
#            self.refreshing = True
#        
#        account_list = account_manager.getCurrentAccount()
#        
#        for account in account_list:
#            account.last_tweet_id = 0
#            account.last_tweet_time = 0
#            
#        self.retrievingData_image.show()
#        self.insertWidget(0, self.retrievingData_image)
#        
#        self.retrievingData = True
#        easy_thread.start(self.retrieveData, args=(account_list, 1, 20), callback=self.updateUI)
#        log.debug('Starting thread')
#        self.currentPage = 2
#        
#        self.emit(SIGNAL('refreshFinished'))
        
    def refresh(self):
        '''
        For debug purpose
        '''
        self.clearAllWidgets()
        
        import random
        account_list = account_manager.getCurrentAccount()
        length = len(account_list)
        rtn = [(account, []) for account in account_list]
        for tweet in json.load(open('doc/json'))['statuses']:
            rtn[random.randrange(0, length)][1].append(tweet)
        self.updateUI(rtn)
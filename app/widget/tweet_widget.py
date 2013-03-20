#coding=utf-8

import imghdr

import time
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from app import constant, theme_manager
from app import logger
from app.widget import picture_viewer

log = logger.getLogger(__name__)

at_terminator = set(''' ~!@#$%^&*()+`={}|[]\;':",./<>?~！￥×（）、；：‘’“”《》？，。''')
url_legal = set('''!#$&'()*+,/:;=?@-._~'''
                + ''.join([chr(c) for c in range(ord('0'), ord('9')+1)])
                + ''.join([chr(c) for c in range(ord('a'), ord('z')+1)])
                + ''.join([chr(c) for c in range(ord('A'), ord('Z')+1)]))

SIGNAL_FINISH = SIGNAL('downloadFinished')
SIGNAL_CLICKED = SIGNAL('clicked')

class Text(QLabel):
    def __init__(self, text, parent=None):
        super(Text, self).__init__(text, parent)
        self.setTextInteractionFlags(Qt.LinksAccessibleByMouse | Qt.TextSelectableByMouse)
        
class TweetText(Text):
    '''
    Widget holding tweet body
    '''
    def __init__(self, text, parent=None):
        super(TweetText, self).__init__(text, parent)
        self.setWordWrap(True)
        
    def resizeEvent(self, ev):
        #print(ev.oldSize().height(), ev.size().height(), self.heightForWidth(ev.oldSize().width()))
        #super(TweetText, self).resizeEvent(ev)
        self.setMaximumHeight(self.heightForWidth(ev.size().width()))
        
class PictureWidget(QLabel):
    '''
    Widget holding avatar and thumbnail
    '''
    
    def __init__(self, parent=None):
        super(PictureWidget, self).__init__(parent)
        
    def mouseReleaseEvent(self, ev):
        if ev.button() == Qt.LeftButton:
            self.emit(SIGNAL_CLICKED)

class PictureTask(QThread):
    '''
    Task to download picture
    '''
    
    def __init__(self, url, manager, widget, size=None):
        super(PictureTask, self).__init__()
        self.url = url
        self.manager = manager
        self.widget = widget
        self.size = size
        
    def run(self):
        try:
            pic_path = self.manager.get(self.url)
            self.emit(SIGNAL_FINISH, self.widget, pic_path, self.size)
        except Exception as e:
            print(e)
            
class GroupBox(QGroupBox):
    def __init__(self, parent=None):
        super(GroupBox, self).__init__(parent)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.setStyleSheet(
            '''
            QGroupBox {
                margin-top: 0px;
                padding-top: 0px;
                border-style: solid;
                border-width: 1px;
            }
            '''
        )

# Global instance of thread pool
#g_thread_pool = QThreadPool.globalInstance()
#g_thread_pool.setMaxThreadCount(6)
#g_thread_pool.setExpiryTimeout(-1)              # Threads never expire

class TweetWidget(QWidget):
    '''
    Widget for each tweet
    '''
    
    def __init__(self, account, tweet, avatar, thumbnail, parent=None):
        '''
        @param account: misc.Account object
        @param tweet: dict of tweet. See doc/插件接口设计.pdf: 单条微博
        @param avatar: QPixmap of user avatar
        @param thumbnail: QMovie showing that the thumbnail is still loading from Internet
        @return: None
        '''
        super(TweetWidget, self).__init__(parent)
        
        self.account = account
        self.tweet = tweet
        self.avatar = avatar
        self.thumbnail = thumbnail
        self.pic_url = ''
        self.time_format = '%Y-%m-%d %H:%M:%S'
        
        self.setupUI()
        self.renderUI()
        self.setSizePolicy(QSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored))
        #self.setStyleSheet('border-style:solid;border-width:5px')
        
        self.connect(self.label_tweet, SIGNAL('linkActivated (const QString&)'), self.onLinkActivated)
        if self.label_retweet:
            self.connect(self.label_retweet, SIGNAL('linkActivated (const QString&)'), self.onLinkActivated)
        if self.label_thumbnail:
            self.connect(self.label_thumbnail, SIGNAL_CLICKED, self.onClicked_Thumbnail)
        
        # Start downloading avatar
        # FIXME: TypeError: updateUI() takes exactly 2 arguments (1 given)
        avatar_url = tweet['user']['avatar_large']
        self.avatar_task = PictureTask(avatar_url, self.account.avatar_manager, self.label_avatar,
            QSize(constant.AVATER_IN_TWEET_SIZE, constant.AVATER_IN_TWEET_SIZE)
        )
        self.connect(self.avatar_task, SIGNAL_FINISH, self.updateUI)
        self.avatar_task.start()
        
        # Start downloading thumbnail if exists
        try:
            if 'thumbnail_pic' in tweet:
                url = tweet['thumbnail_pic']
            elif ('retweeted_status' in tweet) and ('thumbnail_pic' in tweet['retweeted_status']):
                url = tweet['retweeted_status']['thumbnail_pic']
            self.thumbnail_task = PictureTask(url, self.account.picture_manager, self.label_thumbnail)
            self.connect(self.thumbnail_task, SIGNAL_FINISH, self.updateUI)
            self.thumbnail_task.start()
        except UnboundLocalError:
            # No picture
            pass
        
    def onClicked_Thumbnail(self):
        #QMessageBox.information(self, 'test', self.pic_url)
        pic = picture_viewer.PictureViewer(self.pic_url, self.account.picture_manager, self)
        pic.setModal(False)
        pic.show()
        
    def onLinkActivated(self, link):
        #log.debug(link)
        if link.startswith('http'):
            QDesktopServices.openUrl(QUrl(link))

    def findAtEnding(self, src, start):
        i = start
        length = len(src)
        while(i < length):
            if src[i] in at_terminator:
                return i
            i += 1
        return i
    
    def findUrlEnding(self, src, start):
        i = start
        length = len(src)
        while(i < length):
            if src[i] not in url_legal:
                return i
            i += 1
        return i
    
    def findEmotionEnding(self, src, start):
        i = start
        length = len(src)
        prefix_amount = 1       # In case of recursively having emotion expression.
        while(i < length):
            if src[i] == self.account.emotion_exp.prefix:
                prefix_amount += 1
            elif src[i] == self.account.emotion_exp.suffix:
                if prefix_amount == 1:
                    return i + 1
                else:
                    prefix_amount -= 1

            i += 1
        return i + 1
        
    def formatLink(self, src):
        if len(src) == 0:
            return src
        
        if src[0] == '@':
            rtn = '<a style="text-decoration:none" href="user:%s">%s</a>' % (src[1:], src)
        elif src[0] == 'h':
            rtn = '<a style="text-decoration:none" href="%s">%s</a>' % (src, src)
        elif src[0] == self.account.emotion_exp.prefix:
            try:
                emotion_path = self.account.emotion_manager.get(
                    self.account.emotion_dict[src]
                )
                rtn = '<img src="%s" />' % emotion_path
            except KeyError:
                # FIXME: [[xx], [xx] won't be analysed as emotion
                # Maybe emotion can't be found. Analyse the text between prefix and suffix.
                end = len(src) - 1 if src[len(src)-1] == self.account.emotion_exp.suffix else len(src)
                rtn = self.analyse(src[1 : end])
                end_chr = self.account.emotion_exp.suffix if src[len(src)-1] == self.account.emotion_exp.suffix else ''
                rtn = ''.join((src[0], rtn, end_chr))
        else:
            rtn = src
        return rtn
    
    def analyse(self, src):
        # FIXME: find a way to distinguish character and punctuation
        length = len(src)
        i = 0
        target = []
        try:
            while(i < length):
                # At
                if src[i] == '@':
                    end = self.findAtEnding(src, i+1)
                    target.append((i, end))
                    i = end
                # URL
                elif (src[i] == 'h' and src[i+1] == 't' and src[i+2] == 't' and src[i+3] == 'p'):
                    # http
                    if(src[i+4] == 's' and src[i+5] == ':' and src[i+6] == '/' and src[i+7] == '/'):
                        end = self.findUrlEnding(src, i+8)
                        target.append((i, end))
                        i = end
                    # https
                    elif(src[i+4] == ':' and src[i+5] == '/' and src[i+6] == '/'):
                        end = self.findUrlEnding(src, i+7)
                        target.append((i, end))
                        i = end
                # emotion
                elif src[i] == self.account.emotion_exp.prefix:
                    end = self.findEmotionEnding(src, i+1)
                    target.append((i, end))
                    i = end
                    pass
                else:
                    i += 1
        except IndexError:
            pass
        
        if(len(target) == 0):
            target.append((0, len(target)+1))
        
    #    for item in target:
    #        print(src[item[0] : item[1]])
            
        seg_list = []
        try:
            for index,item in enumerate(target):
                seg = src[item[0] : item[1]]
                seg = self.formatLink(seg)
                seg_list.append(seg)
                
                seg = src[ item[1] : target[index+1][0] ]
                seg = self.formatLink(seg)
                seg_list.append(seg)
            pass
        except IndexError:
            seg_list.append(src[ item[1] : ])
            pass
        
        rtn = ''.join(seg_list)
        if not (target[0][0] == 0):
            rtn = src[:target[0][0]] + rtn 
        return rtn

    def updateUI(self, widget, path, size=None):
        '''
        @param widget: QLabel. Widget to be updated
        @param path: string. Image path
        @param size: QSize. Actual size to be painted on the widget
        '''
        pic = QPixmap(path, imghdr.what(path))
        if(size):
            pic = pic.scaled(size, transformMode=Qt.SmoothTransformation)
        widget.setPixmap(pic)
        widget.setFixedSize(pic.size())
        
    def setThumbnail(self, path):
        self.label_thumbnail.setPixmap(QPixmap(path, imghdr.what(path)))
        
    def setupUI(self):
        hLayout = QHBoxLayout()
        hLayout.setContentsMargins(5, 5, 5, 5)
        self.setLayout(hLayout)
        
        # avatar
        v1 = QVBoxLayout()
        hLayout.addLayout(v1)
        self.label_avatar = PictureWidget(self)
        self.label_avatar.setMovie(self.avatar)
        v1.addWidget(self.label_avatar)
        v1.addStretch()
        
        # tweet
        v2 = QVBoxLayout()
        hLayout.addLayout(v2)
        
        ## user, source, service
        h1 = QHBoxLayout()
        v2.addLayout(h1)
        label_user = Text(
            self.analyse('@' + str(self.tweet['user']['screen_name'])), self
        )
        #label_source = QLabel(self.tweet['source'])
        label_service_icon = QLabel(self)
        label_service_icon.setPixmap(QPixmap.fromImage(self.account.service_icon))
        h1.addWidget(label_user)
        #h1.addWidget(label_source)
        h1.addStretch()
        h1.addWidget(label_service_icon)
        
        ## tweet content
        #log.debug('Analysing %s' % self.tweet['text'])
        self.label_tweet = TweetText(
            self.analyse(self.tweet['text']), self
        )
        #log.debug('Done.')
        v2.addWidget(self.label_tweet)
        
        ## retweet if exists
        self.label_thumbnail = None
        self.label_retweet = None
        if('retweeted_status' in self.tweet):
            retweet = self.tweet['retweeted_status']
            
            groupbox = GroupBox(self)
            #groupbox.setContentsMargins(0, 5, 5, 5)
            v2.addWidget(groupbox)
            v3 = QVBoxLayout()
            v3.setContentsMargins(5, 5, 5, 5)
            groupbox.setLayout(v3)
            
            h3 = QHBoxLayout()
            v3.addLayout(h3)
            label_retweet_user = Text(
                self.analyse('@' + retweet['user']['screen_name']), self
            )
            #label_retweet_source = QLabel(retweet['source'])
            h3.addWidget(label_retweet_user)
            #h3.addWidget(label_retweet_source)
            h3.addStretch()
            
            self.label_retweet = TweetText(
                self.analyse(retweet['text']), self
            )
            v3.addWidget(self.label_retweet)
            
            if('thumbnail_pic' in retweet):
                self.pic_url = retweet['original_pic']
                self.label_thumbnail = PictureWidget()
                self.label_thumbnail.setMovie(self.thumbnail)
                v3.addWidget(self.label_thumbnail)
                
            h4 = QHBoxLayout()
            v3.addLayout(h4)
            str_time = time.strftime(self.time_format, time.localtime(retweet['created_at']))
            label_retweet_time = QLabel(str_time, self)
            label_retweet_repost = QLabel('转发(%s)' % str(retweet['reposts_count']), self)
            label_retweet_comment = QLabel('评论(%s)' % str(retweet['comments_count']), self)
            h4.addWidget(label_retweet_time)
            h4.addStretch()
            h4.addWidget(label_retweet_repost)
            h4.addWidget(label_retweet_comment)
        ## No retweet and has picture
        elif('thumbnail_pic' in self.tweet):
            self.pic_url = self.tweet['original_pic']
            self.label_thumbnail = PictureWidget()
            self.label_thumbnail.setMovie(self.thumbnail)
            #self.thumbnail.start()
            v2.addWidget(self.label_thumbnail)
            
        if self.label_thumbnail:
            size = self.label_thumbnail.movie().currentPixmap().size()
            self.label_thumbnail.setFixedSize(size)
        
        ## time, repost, comment
        h2 = QHBoxLayout()
        v2.addLayout(h2)
        str_time = time.strftime(self.time_format, time.localtime(self.tweet['created_at']))
        label_tweet_time = QLabel(str_time, self)
        label_tweet_repost = QLabel('转发(%s)' % str(self.tweet['reposts_count']), self)
        label_tweet_comment = QLabel('评论(%s)' % str(self.tweet['comments_count']), self)
        h2.addWidget(label_tweet_time)
        h2.addStretch()
        h2.addWidget(label_tweet_repost)
        h2.addWidget(label_tweet_comment)
        
        v2.addStretch()
        
    def renderUI(self):
        self.label_avatar.setCursor(QCursor(Qt.PointingHandCursor))
        if self.label_thumbnail:
            self.label_thumbnail.setCursor(QCursor(QPixmap(theme_manager.getParameter('Skin', 'zoom-in-cursor'))))
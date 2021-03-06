import urllib
import urlparse
import xbmcaddon
import xbmcgui
import xbmc
import time
import re
import traceback
import logging
from logging import Handler
import xbmcplugin
from xbmcgui import ListItem
from resources.lib.tor import Subscriptions, SubscriptionsCursor
from resources.lib.offtictor_strings import OffticTorStrings
from BeautifulSoup import BeautifulSoup
from utils import getHtml
import resources.lib.html2text
from resources.lib.html2text import html2text, HTML2Text


try:
    import StorageServer
except:
    import storageserverdummy as StorageServer

dbg = True

from resources.lib import tor
from torhelper import TorPost, TorList, TorFeeds

REMOTE_DBG = False

addon       = xbmcaddon.Addon()
addonpath   = addon.getAddonInfo('path')
addonpath   = xbmc.translatePath(addonpath).decode('utf-8')
addonname   = addon.getAddonInfo('name')
addonid     = addon.getAddonInfo('id')


strings = OffticTorStrings(addon)


# append pydev remote debugger
if REMOTE_DBG:
    # Make pydev debugger works for auto reload.
    # Note pydevd module need to be copied in XBMC\system\python\Lib\pysrc
    try:
        #import pysrc.pydevd as pydevd # with the addon script.module.pydevd, only use `import pydevd`
        import sys
        sys.path.append(addonpath + '../script.module.pydevd/lib/')
        import pydevd
        # stdoutToServer and stderrToServer redirect stdout and stderr to eclipse console
        pydevd.settrace('localhost', stdoutToServer=True, stderrToServer=True)
    except ImportError:
        xbmc.log("Error: " +
            "You must add org.python.pydev.debug.pysrc to your PYTHONPATH.")
        sys.exit(1)


def tratarError(msg):
    var = traceback.format_exc()
    log( var )
    xbmcgui.Dialog().notification(addonname, msg, xbmcgui.NOTIFICATION_ERROR, 7000, True)
   
def log(msg, level=xbmc.LOGDEBUG):
    xbmc.log("|| " + addonid + ": " + msg, level)
    
def route(args):
    output = str(handle)
    output += ','+auth_code
    for arg in args:
        output += ',' + arg
    
    log('route: ' + output)
    
    return output

def set_args():
    global handle
    global auth_code
    global action
    global feed_id
    
    handle = int(sys.argv[1])
    if len(sys.argv)>2:
        auth_code =sys.argv[2]
    if len(sys.argv)>3:
        action =sys.argv[3]
    if len(sys.argv)>4:
        feed_id =sys.argv[4]
    

def feed(feedId, next_pointer=None):
    url_options = ')ung-xunil(02%4.91.1F2%tegW=tnegA-resU|'[::-1]
    try:
        log('feed ID: ' + feedId)

        max_feed_len = int(addon.getSetting("max_feed_len"))
        
        log('max_feed_len:' +  str(max_feed_len))
        try:
            
            try:
                #xbmcgui.Dialog().notification(addonname, strings.get("Connected"))
                torList = TorList()
                serTorList = None
                try:
                    cache.table_name = addonid
                    cachename = "torList_" + str(feedId) + "_"  + str(next_pointer)
                    cachedvalue = cache.get(cachename)
                    log('cached value: ' + cachedvalue)
                    serTorList = eval(cachedvalue)
                    torList.unserialize(serTorList)
                    #serTorList = json.loads(cachedvalue)
                    dummyStr = ''
                except:
                    log('Can not retrieve cache for "' + cachename + '"', xbmc.LOGWARNING)
                    
                if serTorList!=None and serTorList != '':
                    log('Retrieved cache for "' + cachename + '"')
                    #torList = serTorList
                    
                else:
                    torList = TorList()
                    
                search = tor.ItemsSearch(conn)
                unread = []
                try:
                    unread = search.get_unread_only(limit_items=addon.getSetting("max_feed_len"), feed=feedId, stop=True, continuation=next_pointer)
                except:
                    log("no connection, but maybe there's some cache")
                debug = ""
                title = ""
                i = 0
                for item in unread:
                    item.get_details()
                    if item.published > torList.time:
                        '''
                        Add if published after cache time
                        '''
                        yt_id = _find_embeded_youtube(item.mediaUrl)
                        if yt_id != None:
                            item.mediaUrl = _to_youtube_player(yt_id)
                        if item.mediaUrl == None:
                            content = getHtml(item.href)
                            if content:
                                embededAudio = _find_audio(content)
                                yt_id = _find_embeded_youtube(item.content)
                                if embededAudio!=None:
                                    item.mediaUrl = embededAudio + url_options
                                elif yt_id!=None:
                                    item.mediaUrl = _to_youtube_player(yt_id)
                                    #item.mediaUrl = 'RunScript(plugin.video.youtube/play/,' + str(handle) +',?video_id=' + yt_id + ')'
                                    
                        if item.mediaUrl != None:
                            title = item.title
                            
                            #title = item.get('title')
                            torPost = TorPost(item)
                            torList.add_post(torPost)
                            title = "%s" % title.encode('utf-8')
                            log(title, xbmc.LOGDEBUG)
                            xbmcgui.Dialog().notification(addonname, title, icon='', time=0, sound=False)
                            
                            i = i+1
                    else:
                        break
                    if i==max_feed_len:
                        break
                    
                for post in torList.get_post_list():
                         
                    if post.item.mediaUrl != None:
                        title = post.item.title
                        title = "%s" % title.encode('utf-8')
                        log(title, xbmc.LOGDEBUG)
                        
                        li = ListItem()
                        li.setLabel(title)
                        
                        post.item = _fill_post(post.item)
                        
                        
                        li.setInfo('music', {
                            'title': post.item.txtContent,
                            'artist': post.item.author
                        })
                        li.setArt({
                            'icon': post.item.image,
                            'thumb': post.item.image,
                            'poster': post.item.image,
                            'fanart': post.item.image
                        })
                        
                        li.addContextMenuItems([
                            (strings.get('Mark_as_read'),'RunScript(' + addonid + ',' + route(['read', post.item.item_id]) + ')'),
                            (strings.get('Mark_as_unread'),'RunScript(' + addonid + ',' + route(['unread', post.item.item_id]) + ')')
                        ])
                        if False: #post.item.video == True:
                            url = base_url + '?' + urllib.urlencode({'action':'play','handle':str(handle),'video' : post.item.mediaUrl})
                            xbmcplugin.addDirectoryItem(handle, url, li, True)
                        else:
                            xbmcplugin.addDirectoryItem(handle, post.item.mediaUrl, li)
                
                if search.next_pointer != None:
                    li = ListItem()
                    li.setLabel(strings.get('Next_page'))
                    url = base_url + '?' + urllib.urlencode({'action':'feed','handle':str(handle),'auth_code':auth_code, 'feedId' : feedId, 'next_pointer' : search.next_pointer})
                    log(url)
                    xbmcplugin.addDirectoryItem(handle, url, li, True)
                
                
                xbmcplugin.endOfDirectory(handle)
                #xbmcgui.Dialog().select("heading_unread", torList.get_post_list())
                
                cache.table_name = addonid
                # cachename = "torList_" + str(feedId)
                time.localtime()
                #cache.set(cachename,repr(torList))
                #cache.set(cachename, json.dumps(torList))
                torList.time = time.time()
                cache.set(cachename, torList.serialize())
                log("iteration ends", xbmc.LOGDEBUG)
            except:
                tratarError(strings.get("Can_not_connect_TOR"))
        except:
            tratarError(strings.get("Can_not_connect"))
        
        '''    
        debug = ""
        xbmcgui.Dialog().textviewer(addonname, debug)
        '''
    except:    
        tratarError(strings.get('Can_not_start'))

def _to_youtube_player(yt_id):
    return 'plugin://plugin.video.youtube/play/?video_id=' + yt_id

def _find_embeded_youtube(content):
    if content!=None:
        m = re.search("youtube.com/embed/([a-zA-Z\-_0-9]*)", content)
        if m!= None and m.group(1)!=None:
            return m.group(1)
        m = re.search("youtube.com/v/([a-zA-Z\-_0-9]*)", content)
        if m!= None and m.group(1)!=None:
            return m.group(1)
    return None

def _find_audio(content):
    audio_ext = ["ogg", "mp3"]
    embededAudio = None
    soup = BeautifulSoup(content)
    for audio in soup.findAll("audio"):
        #log("AUDIO found")
        embededAudio = audio.source["src"]
        break
    if embededAudio==None:
        for link in soup.findAll("a", {"href": "*"}):
            for ext in audio_ext:
                if link["href"].endswith("." + ext):
                    embededAudio = link["href"]
        
    return embededAudio

def _fill_post(post):
    post.txtContent = ""
    try:
        #log(post.content.encode('utf-8'))
        h = HTML2Text()
        h.ignore_links = True
        h.ignore_images = True
        post.txtContent = h.handle(post.content)
        #log(post.txtContent.encode('utf-8'))
    except:
        post.txtContent = post.content
    
    post.image = None
    soup = BeautifulSoup(post.content)
    for img in soup.findAll("img", limit=1):
        post.image = img["src"]
    return post
       
def my_matching(feed, item):
    log("trying to get audio from content in " + item.href)
    
    content = getHtml(item.href)
    if content!=None:
        soup = BeautifulSoup(content)
        for audio in soup.findAll("audio"):
            log("audio from content in " + item.href)
            return True
        yt_id = _find_embeded_youtube(content)
        return yt_id!=None #<- uncomment when ready to separate video from audio
        #return None
    
    return False
    
    
def feeds():
    serTorFeeds = None
    torFeeds = TorFeeds()
    cachename = "torFeeds"
    prematched = False
    
    try:
        cache.table_name = addonid
        cachedvalue = cache.get(cachename)
        log('cached value for feeds: ' + cachedvalue)
        serTorFeeds = eval(cachedvalue)
        torFeeds.unserialize(serTorFeeds)
    except:
        log('Can not retrieve cache for feeds "' + cachename + '"')
    
    if torFeeds!=None and len(torFeeds.feeds)>0:
        s_list = torFeeds.get_feeds()
        prematched = True
    else:
        subs = Subscriptions(conn, 'audio')
        subs.set_matching(my_matching)
        s_list = subs.get_unread()
        
        
    s_list = sorted(s_list, key=lambda Subscriptions: Subscriptions.firstitemmsec, reverse=True)
    sCursor = SubscriptionsCursor(s_list, 'audio')
    
    nSubs = len(s_list)
    nPodcast = 0
    nGeneric = 0
    nCurrent = 0
    
    progress = xbmcgui.DialogProgress()
    progress.create(strings.get("Loading_subscriptions"), "", "", "")
    
    _update_progress(progress, nSubs, nPodcast, nGeneric, nCurrent)
    
    xbmcgui.Dialog().notification(addonname, strings.get('Subscriptions_preloaded'), icon='', time=0, sound=False)
    feed = sCursor.next(prematched)
    while (feed!=False):
        if progress.iscanceled():
            break
        if feed.matches:
            if not prematched:
                xbmcgui.Dialog().notification(strings.get("Feed_matches"), feed.title, icon='', time=0, sound=False)
                feed.title += ' (' + str(feed.unread_count) + ')'
                torFeeds.add_feed(feed)
            li = ListItem()
            li.setLabel(feed.title)
            li.setArt({
                'icon': feed.iconUrl,
                'thumb': feed.iconUrl,
                'poster': feed.iconUrl,
                'fanart': feed.iconUrl
            })
            url = base_url + '?' + urllib.urlencode({'action':'feed','handle':str(handle),'auth_code':auth_code, 'feedId' : feed.id})
            log(url)
            nPodcast += 1
            li.addContextMenuItems([
                (strings.get('Clear_one_cache'),'RunScript(' + addonid + ',' + route(['clear_one', feed.id]) + ')')
            ])
            xbmcplugin.addDirectoryItem(handle, url, li, True)
            
        else:
            nGeneric += 1
            xbmcgui.Dialog().notification(strings.get("No_feed_matches"), feed.title, icon=xbmcgui.NOTIFICATION_WARNING, time=0, sound=False)
        nCurrent += 1
        _update_progress(progress, nSubs, nPodcast, nGeneric, nCurrent)
        feed = sCursor.next(prematched)
        
    if not prematched:
        cache.set(cachename, torFeeds.serialize())
    
    progress.close()
    if (not progress.iscanceled()):
        xbmcplugin.endOfDirectory(handle, succeeded=True, updateListing=False, cacheToDisc=True)
    
def _update_progress(progress, nSubs, nPodcast, nGeneric, nCurrent):
    perc = (float(nCurrent) / nSubs) * 100
    progress.update( int(perc) , 
        strings.get("Progress_title") + ": " +  str(nCurrent) +" / " + str(nSubs), 
        strings.get("Podcast_blogs") + ": " + str(nPodcast),
        strings.get("Regular_blogs") + ": "  + str(nGeneric))

'''Clear all caches'''
def clear():
    _clear(["torList_%", "torFeeds"])
    
def _clear(keys):
    for key in keys:
        cache.delete(key)
    xbmcgui.Dialog().notification(addonname, strings.get("Cache_cleared"), icon='', time=0, sound=False)
    
def clear_one(feed_id):
    _clear(["torList_" + feed_id + "_%"])

   
def index():
    url = base_url + '?' + urllib.urlencode({'action':'feeds','handle':str(handle),'auth_code':auth_code})
    li = ListItem()
    li.setLabel(strings.get('List_subcriptions'))
    xbmcplugin.addDirectoryItem(handle, url, li, True)
    url = base_url + '?' + urllib.urlencode({'action':'clear','handle':str(handle),'auth_code':auth_code})
    li = ListItem()
    li.setLabel(strings.get('Clear_cache'))
    xbmcplugin.addDirectoryItem(handle, url, li, False)
    url = base_url + '?' + urllib.urlencode({'action':'clear_feeds','handle':str(handle)})
    li = ListItem()
    li.setLabel(strings.get('Clear_Subscriptions_cache'))
    xbmcplugin.addDirectoryItem(handle, url, li, False)
    url = base_url + '?' + urllib.urlencode({'action':'clear_posts','handle':str(handle)})
    li = ListItem()
    li.setLabel(strings.get('Clear_Feeds_cache'))
    xbmcplugin.addDirectoryItem(handle, url, li, False)
    url = base_url + '?' + urllib.urlencode({'action':'settings','handle':str(handle)})
    li = ListItem()
    li.setLabel(strings.get('Open_settings'))
    xbmcplugin.addDirectoryItem(handle, url, li, False)
    
    
    xbmcplugin.endOfDirectory(handle)
    
def play_video(path):
    """
    Play a video by the provided path.

    :param path: Fully-qualified video URL
    :type path: str
    """
    # Create a playable item with a path to play.
    play_item = xbmcgui.ListItem(path=path)
    # Pass the item to the Kodi player.
    xbmcplugin.setResolvedUrl(handle, True, listitem=play_item)

        
    
logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)

handle = None
auth_code = None
action = None
feed_id = None
next_pointer = None
video = None
base_url = sys.argv[0]
args = urlparse.parse_qs(sys.argv[2][1:])

login = addon.getSetting("email")
password = addon.getSetting("password")
conn = tor.Connection(login, password, 'offticTorKodiPlugin')

cache = StorageServer.StorageServer(addonid, 1)
cache.table_name = addonid

set_args()#from contextual menu
if len(args)>0:
    #handle = int(args.get('handle', None))
    auth_code = args.get('auth_code', None)
    if auth_code <> None:
        auth_code = str(auth_code[0])
    action= args.get('action', None)
    if action <> None:
        action = str(action[0])
    feed_id = args.get('feedId', None)
    if feed_id <> None:
        feed_id = str(feed_id[0])
    next_pointer = args.get('next_pointer', None)
    if next_pointer <> None:
        next_pointer = str(next_pointer[0])
    video = args.get('video', None)
    if video <> None:
        video = str(video[0])
    
'''
log('handle: ' + str(handle))
log('autho_code: ' + str(auth_code))
log('base_url: ' + base_url)
log('action:' + str(action))
'''
if auth_code!=None and auth_code.find('?')==-1:
    conn.auth_code=auth_code
else:
    conn.login()
    auth_code = conn.auth_code
    log("Connected")

if action!=None and  feed_id != None:
    
    if action=='read':
        feed = tor.Item(conn, feed_id)
        feed.get_details()
    
        try:
            feed.mark_as_read()
            
            xbmcgui.Dialog().notification(feed.title, strings.get('Marked_as_read'))
        except:
            xbmcgui.Dialog().notification(addonname, strings.get("Can_not_mark_as_read"), xbmcgui.NOTIFICATION_ERROR, 7000, True)
    elif action=='unread':
        feed = tor.Item(conn, feed_id)
        feed.get_details()
    
        try:
            feed.mark_as_unread()
            xbmcgui.Dialog().notification(feed.title, strings.get('Marked_as_unread'))
        except:
            xbmcgui.Dialog().notification(addonname, strings.get("Can_not_mark_as_unread"), xbmcgui.NOTIFICATION_ERROR, 7000, True)
    elif action=='feed':
        feed(feed_id, next_pointer)
    elif action=='clear_one':
        clear_one(feed_id)

elif action=='feeds':
    feeds()
elif action=='clear':
    clear()
elif action=='settings':
    addon.openSettings()
elif action=='clear_feeds':
    _clear(["torFeeds"])
elif action=='clear_posts':
    _clear(["torList_%"])
elif action=='play':
    play_video(video)

else:
    index()
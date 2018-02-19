NAME = 'HGTV'
ART = 'art-default.jpg'
ICON = 'icon-default.jpg'
PREFIX = '/video/hgtv'
BASE_URL = 'http://www.hgtv.com'

FULLEP_URL = 'http://www.hgtv.com/shows/full-episodes'
SHOW_LINKS_URL = 'http://www.hgtv.com/shows/shows-a-z'
VID_PAGE = 'http://www.hgtv.com/videos'

SMIL_NS = {'a': 'http://www.w3.org/2005/SMIL21/Language'}

# Alternative code that pulls all the playlist in a page based on the AssetInfo field for each item showing a number of videos
#  playlist = page.xpath('//span[contains(@class, "AssetInfo") and contains(text(), "Videos")]/ancestor::div[contains(@class, "TextWrap")]/parent::div')
####################################################################################################
def Start():

    ObjectContainer.title1 = NAME
    HTTP.CacheTime = CACHE_1HOUR

####################################################################################################
@handler(PREFIX, NAME, thumb=ICON, art=ART)
def MainMenu():

    oc = ObjectContainer()

    oc.add(DirectoryObject(key = Callback(GetPlaylists, title='Full Episodes', url=FULLEP_URL), title='Full Episodes'))
    oc.add(DirectoryObject(key = Callback(GetPlaylists, title='Videos', url=VID_PAGE), title='Videos'))
    oc.add(DirectoryObject(key = Callback(Alphabet, title='All Shows'), title='All Shows'))

    return oc

####################################################################################################
# This function produces a list of playlists for a video page including the video player and a similar playlists section
# By adding a section code value (other than the default 'ListVideoPlaylist'), you can pull the video playlist from just one section of the page
@route(PREFIX + '/getplaylists')
def GetPlaylists(title, url, section_code='ListVideoPlaylist'):

    oc = ObjectContainer(title2=title)
    main_title = title
    try: page = HTML.ElementFromURL(url)
    except: return ObjectContainer(header='Bad Url', message='The URL for this page is not valid')

    # Check for embedded video player and add a directory
    player_check = page.xpath('//div[@class="m-VideoPlayer"]')
    # Only include the video player directory for URLs with the default section code
    if len(player_check) > 0 and section_code=='ListVideoPlaylist':
        try: player_title = page.xpath('//div[@class="o-VideoPlaylistEmbed__m-Header"]//span/text()')[0]
        except: player_title = "Featured Videos"
        oc.add(DirectoryObject(key=Callback(VideoBrowse, title=player_title, url=url), title=player_title))

    # The playlist for most pages are contained in "Mediabock--playlist" div tags but a few shows return a playlist results list
    playlist = page.xpath('//div[contains(@class, "MediaBlock--playlist") or contains(@class, "m-MediaBlock--PLAYLIST")]')
    # If the playlist is empty or this is a section pull use alternative code
    if len(playlist) < 1 or section_code!='ListVideoPlaylist':
        playlist = page.xpath('//section[contains(@class, "%s")]//div[@class="m-MediaBlock" or contains(@class, "o-Capsule__m-MediaBlock")]' %section_code)

    for item in playlist:
        summary = item.xpath('.//span[contains(@class, "AssetInfo")]/text()')[0].strip()
        if not summary.split()[0].isdigit(): 
            continue
        try: url = item.xpath('.//a/@href')[0]
        except: continue
        url = URLFix(url)
        if not url: 
            continue
        # To bypass any formatting within the title we just join all the data in the title field
        title = ' '.join(item.xpath('.//span[contains(@class, "HeadlineText")]//text()')).strip()
        try: item_thumb = item.xpath('.//img/@data-src')[0]
        except: 
            try: item_thumb = item.xpath('.//img/@src')[0]
            except: item_thumb = thumb

        oc.add(DirectoryObject(
            key = Callback(VideoBrowse, url=url, title=title),
            title = title,
            summary = summary,
            thumb = Resource.ContentsOfURLWithFallback(url=item_thumb)
        ))

    # Check for and create a directory for Video Sections
    section_list = page.xpath('//section[@data-module="video-launcher"]/header/div')
    # Only include this section for Videos
    if len(section_list) > 0 and main_title=='Videos':
        for item in section_list:
            section_title = item.xpath('.//h3/span/text()')[0]
            section_url = item.xpath('.//a/@href')[0]
            section_url = URLFix(section_url)
            oc.add(DirectoryObject(key=Callback(VideoBrowse, title=section_title, url=section_url), title=section_title))

    # Check for and create a directory for Similar Playlists
    playlist_check = page.xpath('//section[contains(@class, "SimilarPlaylists")]//div[@class="m-MediaBlock"]')
    # Do not include the playlist check for URL sent to pull SimilarPlaylists
    if len(playlist_check) > 0 and section_code!='SimilarPlaylists':
        oc.add(DirectoryObject(key=Callback(GetPlaylists, title='Similar Playlists', url=url, section_code='SimilarPlaylists'), title='Similar Playlists'))

    if len(oc) < 1:
        return ObjectContainer(header='Empty', message='There are no full episode shows to list')
    else:
        return oc

####################################################################################################
# A to Z pull for all shows
@route(PREFIX + '/alphabet')
def Alphabet(title):

    oc = ObjectContainer(title2=title)

    for char in HTML.ElementFromURL(SHOW_LINKS_URL, cacheTime = CACHE_1DAY).xpath('//a[contains(@class, "IndexPagination")]/text()'):

        oc.add(DirectoryObject(key=Callback(AllShows, char=char), title=char))
    
    if len(oc) < 1:
        return ObjectContainer(header='Empty', message='There are no items to list')
    else:
        return oc

####################################################################################################
# This function produces a list of shows for letter in Alphabet function
@route(PREFIX + '/allshows')
def AllShows(char):

    oc = ObjectContainer(title2=char)
    page = HTML.ElementFromURL(SHOW_LINKS_URL, cacheTime = CACHE_1DAY)

    for show in page.xpath('//*[@id="%s"]/ancestor::section[contains(@class,"o-Capsule")]//ul/li/a' % (char.lower())):

        title = show.text
        show_url = show.xpath('./@href')[0]
        show_url = URLFix(show_url)
        if not show_url: 
            continue

        oc.add(DirectoryObject(
            key = Callback(GetVideoLinks, show_url=show_url, title=title),
            title = title
        ))

    if len(oc) < 1:
        return ObjectContainer(header='Empty', message='There are no shows to list')
    else:
        return oc
####################################################################################################
# This function pulls the video link from a show's main page since the format of the video page varies
@route(PREFIX + '/getvideolink')
def GetVideoLinks(title, show_url):

    oc = ObjectContainer(title2=title)
    page = HTML.ElementFromURL(show_url, cacheTime = CACHE_1DAY)

    # The Videos link can vary 
    for item in page.xpath('//li[@data-type="sub-navigation-item"]/div'):
        section_title = item.xpath('./a/text()')[0].strip()
        # Skip any the navigation items that are not for videos
        if 'video' not in section_title.lower():
            continue
        section_url = item.xpath('./a/@href')[0]
        section_url = URLFix(section_url)
        if not section_url: 
            continue

        oc.add(DirectoryObject(
            key = Callback(GetPlaylists, url=section_url, title="%s %s" %(title, section_title)),
            title="%s %s" %(title, section_title)
        ))

        # Check for any additional links under the video navigation
        for subitem in item.xpath('./ul[@data-type="dropdown-menu"]/li'):
            sub_url = subitem.xpath('./a/@href')[0]
            sub_url = URLFix(sub_url)
            if not sub_url: 
                continue
            # There is an issue with one drop down that does not have a title
            try: sub_title = subitem.xpath('./a/text()')[0].strip()
            except: sub_title = 'More ' + section_title

            oc.add(DirectoryObject(
                key = Callback(VideoBrowse, url=sub_url, title="%s %s" %(title, sub_title)),
                title="%s %s" %(title, sub_title)
            ))

    if len(oc) < 1:
        return ObjectContainer(header='Empty', message='There are no videos for this show')
    else:
        return oc
####################################################################################################
# This function produces a list of videos from a playlist or a single video from a video player URL
@route(PREFIX + '/videobrowse')
def VideoBrowse(url, title):

    oc = ObjectContainer(title2=title)
    page = HTML.ElementFromURL(url)
    
    try:
        # Some video playlists on HGTV do not contain the inner video player code (div id="video-player_xxxxxx" data-module="video-embed")
        # So we use the outer video container code to pull the json list instead
        json_data = page.xpath('//div[@class="m-VideoPlayer"]//script/text()')[0].strip()
        json = JSON.ObjectFromString(json_data)
    except:
        return ObjectContainer(header='Empty', message='There are no videos to produce on this page')
    #Log('the value of json is %s' %json)
    
    if json:

        # If the URL contains a playlists, create a video for each item in the playlist
        try:
            playlist = json['channels'][0]['videos']
            for video in playlist:

                smil_url = video['releaseUrl']

                if 'link.theplatform.com' in smil_url:
                    oc.add(
                        CreateVideoClipObject(
                            smil_url = smil_url,
                            title = video['title'],
                            summary = video['description'],
                            duration = int(video['length'])*1000,
                            thumb = BASE_URL + video['thumbnailUrl']
                        )
                    )
        
        # Otherwise if the URL just contains one video, create a video item for the single video
        except:
            smil_url = json['video']['releaseUrl']

            if 'link.theplatform.com' in smil_url:
                oc.add(
                    CreateVideoClipObject(
                        smil_url = smil_url,
                        title = json['video']['title'],
                        summary = json['video']['description'],
                        duration = int(json['video']['length'])*1000,
                        thumb = BASE_URL + json['video']['thumbnailUrl']
                    )
                )

    else:
        Log('%s does not contain a video list json or the json is incomplete' % (url))

    # Next page code is needed for shows with playlist results list as well as most HGTV show
    # HGTV shows return a list of videos in its player, so the next page code creates a player for each page of videos listed
    try: next_page = page.xpath('//li[contains(@class, "Pagination")]/a[contains(@class, "NextButton") and not (contains(@class, "is-Disabled"))]/@href')[0]
    except: next_page = None
    if next_page:

        oc.add(NextPageObject(
            key = Callback(GetPlaylists, title=title, url=next_page),
            title = 'Next Page ...'
        ))
        
    if len(oc) < 1:
        return ObjectContainer(header='Empty', message='There are currently no videos for this listing')
    else:
        return oc

####################################################################################################
@route(PREFIX + '/createvideoclipobject', duration=int, include_container=bool)
def CreateVideoClipObject(smil_url, title, summary, duration, thumb, include_container=False, **kwargs):

    videoclip_obj = VideoClipObject(
        key = Callback(CreateVideoClipObject, smil_url=smil_url, title=title, summary=summary, duration=duration, thumb=thumb, include_container=True),
        rating_key = smil_url,
        title = title,
        summary = summary,
        duration = duration,
        thumb = Resource.ContentsOfURLWithFallback(url=thumb),
        items = [
            MediaObject(
                parts = [
                    PartObject(key=Callback(PlayVideo, smil_url=smil_url, resolution=resolution))
                ],
                container = Container.MP4,
                video_codec = VideoCodec.H264,
                audio_codec = AudioCodec.AAC,
                audio_channels = 2,
                video_resolution = resolution
            ) for resolution in [720, 540, 480]
        ]
    )

    if include_container:
        return ObjectContainer(objects=[videoclip_obj])
    else:
        return videoclip_obj

####################################################################################################
@route(PREFIX + '/playvideo', resolution=int)
@indirect
def PlayVideo(smil_url, resolution):

    xml = XML.ElementFromURL(smil_url)
    available_versions = xml.xpath('//a:switch[1]/a:video/@height', namespaces=SMIL_NS)

    if len(available_versions) < 1:
        raise Ex.MediaNotAvailable

    closest = min((abs(int(resolution) - int(i)), i) for i in available_versions)[1]
    video_url = xml.xpath('//a:switch[1]/a:video[@height="%s"]/@src' % closest, namespaces=SMIL_NS)[0]

    return IndirectResponse(VideoClipObject, key=video_url)

####################################################################################################
@route(PREFIX + '/urlfix')
def URLFix(url):

    #Log('the value of url of %s' %url)
    if not url.startswith('http'):
        fixed_url = url
        if url.startswith('//'):
            fixed_url = 'http:' + url
        elif url.startswith('www'):
            fixed_url = 'http://' + url
        elif url.startswith('/'):
            fixed_url = BASE_URL + url
        else:
            Log('unable to fix the url of %s' %url)
            fixed_url = None

    else:
        fixed_url = url
    #Log('the value of fixed_url of %s' %fixed_url)

    return fixed_url

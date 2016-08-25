NAME = 'HGTV'
PREFIX = '/video/hgtv'
BASE_URL = 'http://www.hgtv.com'

FULLEP_URL = 'http://www.hgtv.com/shows/full-episodes'
SHOW_LINKS_URL = 'http://www.hgtv.com/shows/shows-a-z'

SMIL_NS = {'a': 'http://www.w3.org/2005/SMIL21/Language'}

####################################################################################################
def Start():

    ObjectContainer.title1 = NAME
    HTTP.CacheTime = CACHE_1HOUR

####################################################################################################
@handler(PREFIX, NAME)
def MainMenu():

    oc = ObjectContainer()

    oc.add(DirectoryObject(key = Callback(FullEpMenu, title='Full Episodes'), title='Full Episodes'))
    oc.add(DirectoryObject(key = Callback(Alphabet, title='All HGTV Shows'), title='All HGTV Shows'))

    return oc

####################################################################################################
# This function produces a list of shows from the HGTV full episodes page
@route(PREFIX + '/fullepmenu')
def FullEpMenu(title):

    oc = ObjectContainer(title2=title)

    for item in HTML.ElementFromURL(FULLEP_URL).xpath('//div[contains(@class,"2up")]//div[contains(@class, "o-Capsule")]'):
        url = item.xpath('.//a/@href')[0]
        title = item.xpath('.//h4//span/text()')[0].strip()
        thumb = item.xpath('.//img/@data-src')[0]

        oc.add(DirectoryObject(
            key = Callback(VideoBrowse, url=url, title=title),
            title = title,
            thumb = Resource.ContentsOfURLWithFallback(url=thumb)
        ))

    # sort shows in alphabetical order here
    oc.objects.sort(key=lambda obj: obj.title)

    if len(oc) < 1:
        return ObjectContainer(header='Empty', message='There are no full episode shows to list')
    else:
        return oc

####################################################################################################
# A to Z pull for HGTV shows
@route(PREFIX + '/alphabet')
def Alphabet(title):

    oc = ObjectContainer(title2=title)

    for char in HTML.ElementFromURL(SHOW_LINKS_URL).xpath('//section[@class="o-IndexPagination"]//li/a/@title'):

        char_title = char.split('by ')[1]
        oc.add(DirectoryObject(key=Callback(AllShows, char=char_title), title=char_title))
    
    if len(oc) < 1:
        return ObjectContainer(header='Empty', message='There are no shows to list')
    else:
        return oc

####################################################################################################
# This function produces a list of all HGTV Shows based on letter chosen in Alphabet function
@route(PREFIX + '/allshows')
def AllShows(char):

    oc = ObjectContainer(title2=char)

    for show in HTML.ElementFromURL(SHOW_LINKS_URL).xpath('//*[@id="%s"]/ancestor::section[contains(@class,"o-Capsule")]//ul/li/a' % (char.lower())):

        title = show.text
        show_url = show.xpath('./@href')[0]

        oc.add(DirectoryObject(
            key = Callback(GetVideoLinks, show_url=show_url, title=title),
            title = title
        ))

    if len(oc) < 1:
        return ObjectContainer(header='Empty', message='There are no shows to list')
    else:
        return oc

####################################################################################################
# This function pulls the video link and any pull downs for it from a show's main page
@route(PREFIX + '/getvideolinks')
def GetVideoLinks(title, show_url):

    oc = ObjectContainer(title2=title)
    data = HTML.ElementFromURL(show_url)

    for section in data.xpath('//li[@data-type="sub-navigation-item"]/div'):
        try: section_url = section.xpath('./a[contains(text(), "Videos")]/@href')[0]
        except: continue
        section_title = section.xpath('./a/text()')[0]
        oc.add(DirectoryObject(key = Callback(VideoBrowse, url=section_url, title=section_title), title = section_title))

        for item in section.xpath('./ul/li/a'):
            url = item.xpath('./@href')[0]
            title = item.xpath('.//text()')[0]

            oc.add(DirectoryObject(
                key = Callback(VideoBrowse, url=url, title=title),
                title = title
            ))

    if len(oc) < 1:
        oc.add(DirectoryObject(key = Callback(VideoBrowse, url=show_url, title=title), title = "Featured Videos"))

    return oc

####################################################################################################
# This function produces a list of videos for any page with a video player in it 
@route(PREFIX + '/videobrowse')
def VideoBrowse(url, title):

    oc = ObjectContainer(title2=title)
    main_title = title
    page = HTML.ElementFromURL(url)

    # To prevent any issues with URLs that do not contain the video playlist json, we put the json pull in a try/except
    try:
        json_data = page.xpath('//div[contains(@class, "VideoPlayer") or contains(@class,"video-player")]//script/text()')[0].strip()
        json = JSON.ObjectFromString(json_data)
    except:
        json = None

    if json:

        for video in json['channels'][0]['videos']:

            smil_url = video['releaseUrl']

            if not 'link.theplatform.com' in smil_url:
                continue

            title = video['title'].replace('&amp,', '&')
            summary = video['description']
            duration = int(video['length'])*1000
            thumb = BASE_URL + video['thumbnailUrl']

            oc.add(
                CreateVideoClipObject(
                    smil_url = smil_url,
                    title = title,
                    summary = summary,
                    duration = duration,
                    thumb = thumb
                )
            )

    else:
        Log('%s does not contain a video list json or the json is incomplete' % (url))

    # Next page code
    try: next_url = page.xpath('//li/a[text()= "Next"]/@href')[0]
    except: next_url = ''
    if next_url:
        oc.add(NextPageObject(key = Callback(VideoBrowse, title=main_title, url=next_url),title = L("Next Page ...")))
        
    if len(oc) < 1:
        return ObjectContainer(header='Empty', message='There are currently no videos for this show')
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

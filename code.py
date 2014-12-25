import web
import threading
import flickrapi
import flickrapi.exceptions
import urllib
import os

API_KEY = '7c1331700a70376959f0ac13c4fa09e9'
SECRET = 'b8560eb50a720515'
flickr = flickrapi.FlickrAPI(API_KEY)
DOWNLOAD = '/downloads/'

urls = (
    '/', 'index',
    '/result', 'result',
    '/next/(.*)', 'next',
)

render = web.template.render('templates/')

# global function getting and returning search results
def search(param):
    thumbs = []
    orgs = []
    pid = []

    try:
        search_resp = flickr.photos_search(**param)
        if search_resp.attrib['stat'] == 'ok':
            p = search_resp.find('photos')
            num = p.attrib['total']
            photos = p.findall('photo')
            if photos:
                for x in photos:
                    thumbs.append(x.attrib['url_t'])
                    pid_ = x.attrib['id']
                    pid.append(pid_)
                    url = flickr.photos_getInfo(photo_id = pid_)
                    if url.attrib['stat'] == 'ok':
                        orgs.append(url.find('photo').find('urls').find('url').text)
    except flickrapi.exceptions.FlickrError:
        pass

    return num, pid, thumbs, orgs, param

class index:
    def GET(self):
        return render.index()

class result:
    # set parameter of search appropriately and call search
    def setParam(self, user_in, tags_in, text_in, minUpload, maxUpload, minLong, maxLong, minLat, maxLat, page_in):
        user = ''
        box = ''
        
        if user_in != "":
            try:
                id_resp = flickr.people_findByUsername(username = user_in)
                if id_resp.attrib['stat'] == 'ok':
                    user = id_resp.find('user').attrib['id']
            except flickrapi.exceptions.FlickrError:
                pass
        if minLong != "" and maxLong != "" and minLat != "" and maxLat != "":
            box = minLong + ", " + minLat + ", " + maxLong + ", " + maxLat

        param = dict (user_id = user,
                       tags = tags_in,
                       text = text_in,
                       min_upload_date = minUpload,
                       max_upload_date = maxUpload,
                       bbox = box,
                       extras = 'url_t',
                       per_page = 20,
                       page = page_in)
        return search(param)
    
    # get user input
    def POST(self):
        i = web.input()
        n, i, t, l, p = self.setParam(i.ui, i.tg, i.tx, i.mnu, i.mxu, i.mnlong, i.mxlong, i.mnlat, i.mxlat, 1)
        return render.result(n, i, t, l, p)

class next:
    # render next search results page
    def GET(self, param):
        p = eval(param)
        p['page'] += 1
        num, pid, thumbs, links, params = search(p)
        return render.result(num, pid, thumbs, links, params)
    
    # download photo to DOWNLOAD directory in the background
    def longrunning(self, w):
        for i in w:
            try:
                search_sizes = flickr.photos_getSizes(photo_id = int(i))
                if search_sizes.attrib['stat'] == 'ok':
                    s = search_sizes.find('sizes').findall('size')
                    if s:
                        org = s[len(s) - 1].attrib['source']
                        urllib.urlretrieve(org, os.getcwd() + DOWNLOAD + i + '.jpg')
            except flickrapi.exceptions.FlickrError:
                print "Could not download" + i
        print "Finished download."
    
    # direct user page to next search results while downloading
    def POST(self, param):
        print "Downloading image(s)..."
        w = web.input().keys()
        thread = threading.Thread(target = self.longrunning, args = [w])
        thread.start()
        return self.GET(param)

if __name__ == "__main__":
    app = web.application(urls, globals())
    app.run()

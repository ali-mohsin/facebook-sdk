from facebook import get_user_from_cookie, GraphAPI
from threading import Thread

import requests

def id2page(iden,token):
    graph = GraphAPI(token)
    pages = graph.get_object('me/accounts')
    for page in pages['data']:
        if iden == page['id']:
            return page


def post_message(msg,session):
    graph = GraphAPI(session['page']['access_token'])
    att = {}
    att['published'] = session['visibility']
    return graph.put_wall_post(msg,attachment=att);

def getposts(is_published,token,session):
    graph = GraphAPI(token)
    args={}
    args['access_token'] = token
    args['is_published'] = is_published
    feed = requests.request("GET", "https://graph.facebook.com/" + session['page']['id'] + "/promotable_posts",params=args).json()
    return posts_from_one_page(feed,graph,token)
    
def posts_from_one_page(feed,graph,token):
    ret = {}
    posts = []
    views = [None]*25
    ret['next'] = None
    ret['posts'] = None
    threads = []
    index = 0
    try:
        for post in feed['data']:
            cur = {}
            if 'message' in post:
                cur['text'] = post['message']
            elif 'story' in post:
                cur['text'] = post['story']

            thread = Thread(target = get_views,args=(post['id'],graph,views,index,token))
            thread.start()
            index+=1
            threads.append(thread)
            # cur['views'] = get_views(post['id'],graph)
            posts.append(cur)

        for t in threads:
            t.join()

        for i in range (0,index):
            posts[i]['views'] = views[i]

        ret['next'] = feed['paging']['next'];
        ret['posts'] = posts
    except KeyError:
        return ret
    return ret

def get_views(id,graph,res,ind,token): # TODO: Change API for this
    args={}
    args['access_token'] = token
    ans = requests.request("GET", "https://graph.facebook.com/" + id + "/insights/post_impressions",params=args).json()['data'][0]['values'][0]['value']#/post_impressions_unique")
    res[ind] = ans
    print res[ind]
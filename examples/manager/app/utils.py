from facebook import get_user_from_cookie, GraphAPI
from threading import Thread


def get_pages(graph):
    accounts = graph.get_object('me/accounts')
    return accounts['data']


def id_to_page(id, graph):
    pages = graph.get_object('me/accounts')
    for page in pages['data']:
        if id == page['id']:
            return page


def post_message(msg, page_token, is_visible):
    graph = GraphAPI(page_token)
    att = {'published' : is_visible}
    return graph.put_wall_post(msg,attachment=att);

def get_posts(graph, is_published, id):
    args = {'is_published' : is_published}
    feed = graph.request(id+"/promotable_posts",args = args)
#    get_connections(id, 'promotable_posts', args = args)
    return posts_from_one_page(feed,graph)
    
def posts_from_one_page(feed,graph): #TODO
    MAX_THREADS = 25
    posts = []
    pending = []
    views = [None]*MAX_THREADS 
    index = 0
    ret = {}
    try: 
        for post in feed['data']:
            text = post['message'] if 'message' in post else post['story']
            posts.append(text)
            view_request = Thread(target = get_views, args = (post['id'], graph, views, index))
            view_request.start()
            pending.append(view_request)
            index+=1
        wait_for(pending)
        ret = {
            'posts' : posts,
            'views' : views,
            'next' : feed['paging']['next']   
        }

    except KeyError:
        return {'posts' : None, 'views': None, 'next': None}

   
 
    return ret


def wait_for(pending):
    for req in pending:
        req.join()

def get_views(id, graph, res, ind): 
    resp = graph.get_connections(id, "insights/post_impressions")
    count = resp['data'][0]['values'][0]['value']
    res[ind] = count

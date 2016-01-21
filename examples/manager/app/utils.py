from facebook import get_user_from_cookie, GraphAPI
from threading import Thread


def get_pages(graph):
    """Just fetch all the pages using Facebook SDK wrapper call"""

    accounts = graph.get_object('me/accounts')
    return accounts['data']


def id_to_page(id, graph):
    """Translate from page id to all page info

    Iterate through all of user's accounts and 
    return the account that matches with the id

    NOTE: Currently O(n) op, can be optimized by hashtable
    """

    pages = graph.get_object('me/accounts')
    for page in pages['data']:
        if id == page['id']:
            return page


def post_message(msg, page_token, is_visible):
    """ Push a post as the page

    Use published attribute to distinguish between (Un)published posts
    """

    graph = GraphAPI(page_token)
    att = {'published' : is_visible}
    return graph.put_wall_post(msg,attachment=att);

def get_posts(graph, is_published, id):
    """ Fetch posts for the first page from given page's feed

    Use a raw request to trigger Facebook Graph API with promotable_posts
    showing both published and unpublished posts which can be seperated by
    using is_published attribute
    """

    args = {'is_published' : is_published}
    feed = graph.request(id+"/promotable_posts",args = args)
    return posts_from_one_page(feed,graph)
    
def posts_from_one_page(feed,graph): #TODO
    """ Just fetches all the posts from a given page

    Iterate through all the messages in the feed and record their text/story
    depending on the post type.

    For views, multiple threads are launched, one for each request so that 
    its an asynchronous process not affecting the overall latency of the op.

    Function waits for all the threads to finish before returning the answer

    Last page will result in a KeyError exception which will be caught and fields
    will be returned as null instead which is later checked in the html file 
    """

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
    """Just join all the pending threads with the Current thread
    """
    for req in pending:
        req.join()

def get_views(id, graph, res, ind): 
    """Fetch the insights by triggering post_impressions attribute

    The response is the parsed and only the view count is returned
    """

    resp = graph.get_connections(id, "insights/post_impressions_unique")
    count = resp['data'][0]['values'][0]['value']
    res[ind] = count

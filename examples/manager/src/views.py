from facebook import get_user_from_cookie, GraphAPI
from flask import g, render_template, redirect, request, session, url_for
from threading import Thread


from app import app, db
from models import User
import requests

# Facebook app details
FB_APP_ID = '457777107745813'
FB_APP_NAME = 'pagemanagerinterview'
FB_APP_SECRET = '1f8fa38915fcfa581abf238821fa07a1'


@app.route('/pagemain',methods=['POST'])
def pagemain():
    session['page'] = id2page(request.form['page'])
    return render_template('do_action.html', user = g.user)


def id2page(iden):
    token = g.user['access_token']
    graph = GraphAPI(token)
    pages = graph.get_object('me/accounts')
    for page in pages['data']:
        if iden == page['id']:
            return page



@app.route('/input_post',methods=['POST'])
def input_post():
    message = request.form['message']
    resp = post_message(message)
    return render_template('success.html', user = g.user, post_id = resp['id'])

def post_message(msg):
    graph = GraphAPI(session['page']['access_token'])
    att = {}
    att['published'] = session['visibility']
    return graph.put_wall_post(msg,attachment=att);

def getposts(is_published):
    token = g.user['access_token']
    graph = GraphAPI(token)
    args={}
    args['access_token'] = token
    args['is_published'] = is_published
    feed = requests.request("GET", "https://graph.facebook.com/" + session['page']['id'] + "/promotable_posts",params=args).json()
    return posts_from_one_page(feed,graph)
    
def posts_from_one_page(feed,graph):
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

            thread = Thread(target = get_views,args=(post['id'],graph,views,index,g.user['access_token']))
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

@app.route('/renderresult',methods=['POST'])
def renderresult():
    action = request.form['action']
    session['visibility'] = request.form['vis'] == 'pub'
    if(action == 'list'):
        resp = getposts(session['visibility'])
        return render_template('display_posts.html', user = g.user, posts = resp['posts'], next = resp['next'])
    elif (action == 'add'): 
        return render_template('input_post.html', user = g.user)
    else:
        return redirect(url_for('pagemain'))

@app.route('/rendernext',methods = ['POST'])
def rendernext():
    token = g.user['access_token']
    graph = GraphAPI(token)

    url = request.form['next']
    feed = requests.get(url).json()
    resp = posts_from_one_page(feed,graph);
    # if(resp['next'] == None)
    #     resp['next'] = "None"
    print resp
    return render_template('display_posts.html', user = g.user, posts = resp['posts'], next = resp['next'])


@app.route('/pagemainred')
def pagemainred():
    return render_template('do_action.html', user = g.user)

@app.route('/')
def index():
    # If a user was set in the get_current_user function before the request,
    # the user is logged in.

    if g.user != None:
        return render_template('index.html', app_id=FB_APP_ID,
                               app_name=FB_APP_NAME, user=g.user)
    # Otherwise, a user is not logged in.
    return render_template('login.html', app_id=FB_APP_ID, name=FB_APP_NAME)

@app.route('/displaypages')
def displaypages():
    pages = getpages()['data']
    return render_template('display.html', app_id=FB_APP_ID,app_name=FB_APP_NAME, user=g.user, pages = pages)


def getpages():
    graph = GraphAPI(g.user['access_token'])
    accounts = graph.get_object('me/accounts')
    return accounts


@app.route('/logout')
def logout():
    """Log out the user from the application.

    Log out the user from the application by removing them from the
    session.  Note: this does not log the user out of Facebook - this is done
    by the JavaScript SDK.
    """
    session.pop('user', None)
    return redirect(url_for('index'))


@app.before_request
def get_current_user():
    """Set g.user to the currently logged in user.

    Called before each request, get_current_user sets the global g.user
    variable to the currently logged in user.  A currently logged in user is
    determined by seeing if it exists in Flask's session dictionary.

    If it is the first time the user is logging into this application it will
    create the user and insert it into the database.  If the user is not logged
    in, None will be set to g.user.
    """

    # Set the user in the session dictionary as a global g.user and bail out
    # of this function early.
    if session.get('user'):
        g.user = session.get('user')
        return

    # Attempt to get the short term access token for the current user.
    result = get_user_from_cookie(cookies=request.cookies, app_id=FB_APP_ID,
                                  app_secret=FB_APP_SECRET)

    # If there is no result, we assume the user is not logged in.
    if result:
        # Check to see if this user is already in our database.
        user = User.query.filter(User.id == result['uid']).first()

        if not user:
            # Not an existing user so get info
            graph = GraphAPI(result['access_token'])
            profile = graph.get_object('me')
            if 'link' not in profile:
                profile['link'] = ""

            # Create the user and insert it into the database
            user = User(id=str(profile['id']), name=profile['name'],
                        profile_url=profile['link'],
                        access_token=result['access_token'])
            db.session.add(user)
        elif user.access_token != result['access_token']:
            # If an existing user, update the access token
            user.access_token = result['access_token']

        # Add the user to the current session
        session['user'] = dict(name=user.name, profile_url=user.profile_url,
                               id=user.id, access_token=user.access_token)

    # Commit changes to the database and set the user as a global g.user
    db.session.commit()
    g.user = session.get('user', None)

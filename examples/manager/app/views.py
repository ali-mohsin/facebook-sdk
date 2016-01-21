from facebook import get_user_from_cookie, GraphAPI
from flask import g, render_template, redirect, request, session, url_for
import utils

from app import app, db
from models import User
import requests

# Facebook app details
FB_APP_ID = '457777107745813'
FB_APP_NAME = 'pagemanagerinterview'
FB_APP_SECRET = '1f8fa38915fcfa581abf238821fa07a1'



@app.route('/pagemain',methods=['POST'])
def page_main():
    """ Show all the possible actions a user can do

    Take the page id from the form and convert into page using helper
    function id_to_page.
 
    """
    
    cur_page = request.form['page']
    session['page'] = utils.id_to_page(cur_page,g.graph)
    return render_template('do_action.html')

@app.route('/input_post',methods=['POST'])
def input_post(): #TODO, error handling for privacy checks
    """ Write a post to the current page.

    Assumes the post should be written by the page (NOT by the user)
    visibility field identifies if this is a published or unpublished post
    """

    message = request.form['message']
    page_token = session['page']['access_token']
    resp = utils.post_message(message, page_token, session['visibility'])
    return render_template('success.html', post_id = resp['id'])

@app.route('/renderresult',methods=['POST'])
def render_result():
    """ Redirects to respective pages according to the action chosen by user

    First page of posts are fetched using the utils method get_posts. Views and Text is passed
    onto html for display.

    For add, redirected to an html page to input text.
    """

    action = request.form['action']
    session['visibility'] = request.form['vis'] == 'pub'
    if(action == 'list'):
        resp = utils.get_posts(g.graph,session['visibility'],session['page']['id'])
        return render_template('display_posts.html', data = resp, next = resp['next'])
    elif (action == 'add'): 
        return render_template('input_post.html')
    else:
        return redirect(url_for('error')) #TODO: add this page

@app.route('/rendernext',methods = ['POST'])
def rendernext():
    """ Fetches the corresponding page for displaying posts.

    "Next" field identifies the url for next page. Simple Json request
    fetches the page and forwards the result tp html
    """

    url = request.form['next']
    feed = requests.get(url).json()
    resp = utils.posts_from_one_page(feed,g.graph)
    return render_template('display_posts.html', data = resp, next = resp['next'])

@app.route('/pagemainred')
def pagemainred():
    """ Page to redirect to actions page
    """
    return render_template('do_action.html')


@app.route('/displaypages')
def display_pages():
    """ Show options of all the pages a user manages
    """
    pages = utils.get_pages(g.graph)
    return render_template('display.html', app_id=FB_APP_ID,app_name=FB_APP_NAME, user=g.user, pages = pages)


#################### BOILER PLATE CODE STARTS HERE ###################

@app.route('/')
def index():
    # If a user was set in the get_current_user function before the request,
    # the user is logged in.

    if g.user:
        return render_template('index.html', app_id=FB_APP_ID,
                               app_name=FB_APP_NAME, user=g.user)
    # Otherwise, a user is not logged in.
    return render_template('login.html', app_id=FB_APP_ID, name=FB_APP_NAME)



@app.route('/logout')
def logout():
    """Log out the user from the application.

    Log out the user from the application by removing them from the
    session.  Note: this does not log the user out of Facebook - this is done
    by the JavaScript SDK.
    """
    session.pop('user', None)
#    g.user = None
#    g.graph = None
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
        g.graph = GraphAPI(g.user['access_token'])
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
            g.graph = graph
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

from flask import Flask , request , abort , jsonify , g, Response, _app_ctx_stack
from datetime import datetime
from flask_basicauth import BasicAuth
from werkzeug import check_password_hash, generate_password_hash
from cassandra.cluster import Cluster
import uuid
import json

app = Flask(__name__)

# Connect to Cassandra Cluster
cluster = Cluster(['172.17.0.2'])

#************************************Basic Authentication****************************************
class DiscussionForumBasicAuth(BasicAuth):
    def __init__(self, app=None):
        if app is not None:
            self.app = app
            self.init_app(app)
        else:
            self.app = None

    def check_credentials(self, username, password):
        if username != None and password != None:
            user = cql_query_db('select * from user where username = ?', [username], one=True)
            print(user[1])
            if user != None:
                if user[2] == username and check_password_hash(user[1], password):
                    return 'true'
                else:
                    return None
            else:
                return None
        else:
            return None


basic_auth = DiscussionForumBasicAuth(app)

#***************Get Cassandra connection from cluster**********************
def get_db():
    top = _app_ctx_stack.top
    if not hasattr(top, 'cassandra_cluster'):
        print('<--Existing context not found for cassandra cluster-->')
        top.cassandra_cluster = cluster.connect()
    return top.cassandra_cluster

#*****************initialize and populate Database************************
@app.cli.command('initdb')
def initdb_command():
    """Creates the database tables."""
    db = get_db()
    print('Initialized the database.')

    create_schema(db)
    print('<---Schema Created Sucessfully--->')

    populate_database(db)
    print('<-- Populated Schema Sucessfully-->')

#Create Cassandra Schema
def create_schema(session):
    print('<--Inside of Init Schema-->')
    with open('createSchema.cql') as f:
        for line in f:
            session.execute(line)
        print('<---Completed create Schema--->')

#Populate dummy data into Cassandra
def populate_database(session):
    print('<--- Inside populateDatabase --->')

    cql_file = open('populateDatabase.cql')
    cql_command_list = ''.join(cql_file.readlines()).split(";")

    batch_query = "BEGIN BATCH "

    for line in cql_command_list:
        batch_query = batch_query + line

	batch_query = batch_query + " APPLY BATCH;"
    prepared_stmt = session.prepare(batch_query)
    session.execute(prepared_stmt)

# getdb for Cassandra
def getdb():
    """Opens a new database connection if there is none yet for the
     current application context.
     """
    top = _app_ctx_stack.top
    if not hasattr(top, 'cassandra_cluster'):
        print('<--Existing context not found for cassandra cluster-->')
        top.cassandra_cluster = cluster.connect('discussionforum')
    return top.cassandra_cluster

def cql_query_db(query, args=(), one=False):
    prepared_stmt = getdb().prepare(query)
    print(prepared_stmt)
    rv = get_db().execute(prepared_stmt, args)
    return (rv[0] if rv else None) if one else rv

#********************************User API's**********************************************
@app.route('/users', methods=['POST'])
def register_user():
    if request.method == 'POST':
        if not request.json:
            abort(400)
        else:
            db = getdb()
            db.execute('''insert into user (
                          user_id, username, password) values (%s, %s, %s)''',
                       [uuid.uuid1(),request.json.get('username'), generate_password_hash(request.json.get('password'))])
    return jsonify({'message': 'Successfully registered'}), 201


def get_user_name(username):
    print('-----get user name-----------')
    print(username)
    rv = cql_query_db('select user_id from user where username = ?',[username], one=True)
    print('-----------record fetched-------- in get username')
    return rv[0] if rv else None


@app.route('/users/<username>', methods=['PUT'])
@basic_auth.required
def update_user(username):
        userid = get_user_name(username)
        if userid is None:
            return jsonify({"message": "user with that name not found"}), 404

        if request.authorization.username != username:
            return jsonify({"message": "conflicted user"}), 409
        print(username)
        db = getdb()

        db.execute('''update DiscussionForum.user set username=%s, password=%s where user_id=%s''',[request.json.get('username'),generate_password_hash(request.json.get('password')),userid])
        return jsonify({"message": "user updated successfully"}), 200

#**************************Forum API's**********************************************
def get_forum_id(name):
    rv = cql_query_db('SELECT forum_id from forum where name = ?',[name], one=True)
    return rv[0] if rv else None

def get_forum_name(name):
    rv = cql_query_db('select name from forum where name = ?', [name], one=True)
    return rv[0] if rv else None

@app.route('/forums', methods=['GET'])
def get_forum():

    forums = cql_query_db('select * from forum', [], one=False)
    forum_info = []
    if forums is None:
        abort(404)
    else:
        for forum in forums:
            forum_info.append({"id": forum[0], "name": forum[2], "creator": forum[1]})
    return jsonify({'Forums': forum_info}), 200

# Forum Post
@app.route('/forums', methods=['POST'])
@basic_auth.required
def post_forums():

    if get_forum_name(request.json.get('name')):
        return jsonify({"message": "forum with that name already exists"}), 409
    db = getdb()
    db.execute('''insert into forum (
                              forum_id, creator, name) values (%s, %s, %s)''',
               [uuid.uuid1(), request.authorization.username, request.json.get('name')])

    forum_id = get_forum_id(request.json.get('name'))
    resp = Response(status=201, mimetype='application/json')
    resp.headers['Location'] = 'http://127.0.0.1:5000/forums/' + str(forum_id)
    return resp
	

#**********************************Thread API's**********************************************
def get_thread_id(title):
    rv = cql_query_db('SELECT thread_id from thread_post where title = ?',[title], one=True)
    return rv[0] if rv else None

def check_forum_exist(forum_id):
    rv = cql_query_db('SELECT forum_id from forum where forum_id = ?',[uuid.UUID(forum_id)], one=True)
    return rv[0] if rv else None

#Thread GET
@app.route('/forums/<forum_id>', methods=['GET'])
def get_threads(forum_id):

    forum = check_forum_exist(forum_id)
    if forum is None:
        return jsonify({"message": "forum not found"}), 404

    threads = cql_query_db(''' SELECT thread_id, title, creator, timestamp
                            from thread_post where forum_id = ?
                             ALLOW FILTERING''', [uuid.UUID(forum_id)])

    threadlist = []
    if threads:
        for thread in threads:
            threadlist.append(thread)

    # Start: Sort the threads in Descending order
        response_data = jsonify(threadlist)
        desc_list_json = response_data.get_data(as_text=True)
       
        response_json = json.loads(desc_list_json)
       
        sorted_json_list = sorted(response_json, key=lambda i: i[3], reverse=True)
    # End: Sort the threads in Descending order

        return jsonify({'Threads': sorted_json_list}), 200
    return {}, 404

# Thread Post
@app.route('/forums/<forum_id>', methods=['POST'])
@basic_auth.required
def post_threads(forum_id):

    forum = check_forum_exist(forum_id)
    if forum is None:
        return jsonify({"message": "forum not found"}), 404

    request_content = request.get_json(force=True)
    db = getdb()
	
	#Form a Post JSON Object
    postList = []
    data = {
        "author": request.authorization.username,
        "text": request_content['text'],
        "timestamp": datetime.isoformat(datetime.now())
    }

    json_string = json.dumps(data)
    postList.append(json_string)

    insert_stmt = db.prepare("INSERT INTO thread_post (thread_id, forum_id, title, creator, timestamp, posts) VALUES (?, ?, ?, ?, ?, ?)")
    db.execute(insert_stmt,
               [uuid.uuid1(), uuid.UUID(forum_id), request_content['title'], request.authorization.username,
                datetime.now(), postList])

    thread_id = get_thread_id(request_content['title'])
    resp = Response(status=201, mimetype='application/json')
    resp.headers['Location'] = 'http://127.0.0.1:5000/forums/' + str(forum_id) + '/' + str(thread_id)
    return resp


#****************************Post API's**********************************************
def checkExist(thread_id, forum_id):
    rv = cql_query_db('SELECT thread_id from thread_post where thread_id = ? and forum_id = ?',[uuid.UUID(thread_id),uuid.UUID(forum_id)], one=True)
    return rv[0] if rv else None

#Post GET
@app.route('/forums/<forum_id>/<thread_id>', methods=['GET'])
def get_posts(forum_id, thread_id):
    forumThread = checkExist(thread_id, forum_id)
    if forumThread is None:
        return jsonify({"message": "forum/thread not found"}), 404

    posts = cql_query_db('''SELECT posts from thread_post where forum_id = ? and thread_id = ? ALLOW FILTERING''', [uuid.UUID(forum_id), uuid.UUID(thread_id)], one=False)
    print('data from db')
    print(posts)
    postlist = []
    if posts:
        for post in posts:
            postlist.append(post)
       
        # Start: Sort the threads in Descending order
        response_data = jsonify(postlist)
        desc_list_json = response_data.get_data(as_text=True)
        response_json = json.loads(desc_list_json)
        sorted_json_list = sorted(response_json, key=lambda i: i['timestamp'], reverse=True)
        # End: Sort the threads in Descending order

        return jsonify({'Posts': postlist}), 200
    return {}, 404

#Post POST
@app.route('/forums/<forum_id>/<thread_id>', methods=['POST'])
@basic_auth.required
def post_posts(forum_id, thread_id):

    forumThread = checkExist(thread_id, forum_id)
    if forumThread is None:
        return jsonify({"message": "forum/thread not found"}), 404

    rv = cql_query_db('select posts from thread_post where thread_id = ?', [uuid.UUID(thread_id)], one=True)
    getPostList = rv.posts
    request_content = request.get_json(force=True)
    db = getdb()

	# Form a Post JSON Object
    data = {
        "author": request.authorization.username,
        "text": request_content['text'],
        "timestamp": datetime.isoformat(datetime.now())
    }

    json_string = json.dumps(data)
    getPostList.append(json_string)

    update_stmt = db.prepare(
        "update thread_post set posts = ?, timestamp = ? where thread_id = ? and forum_id = ?")
    db.execute(update_stmt,
               [getPostList, datetime.now(), uuid.UUID(thread_id), uuid.UUID(forum_id)])

    resp = Response(status=201, mimetype='application/json')
    return resp


if __name__ == '__main__':
    app.run(debug=True)
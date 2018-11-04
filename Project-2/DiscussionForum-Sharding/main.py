from datetime import datetime
import flask
import csv
import uuid
from flask import jsonify, request, g, _app_ctx_stack
from flask import Response
from flask_restful import reqparse
from werkzeug import check_password_hash, generate_password_hash
from flask_basicauth import BasicAuth
import sqlite3

app = flask.Flask('discussion_forum')
app.config.from_object(__name__)
app.config.from_envvar('DISCUSSIONFORUMAPI_SETTINGS', silent=True)
app.config["DEBUG"] = True

# List of sharding databases
DATABASES = '/tmp/discussionformapi00.db', '/tmp/discussionformapi01.db', '/tmp/discussionformapi02.db'
DATABASE = '/tmp/discussionformapi.db'
PER_PAGE = 30
SECRET_KEY = b'_3myapplication'

print("Registering GUIDs...")
sqlite3.register_converter('GUID', lambda b: uuid.UUID(bytes_le=b))
sqlite3.register_adapter(uuid.UUID, lambda u: u.bytes_le)
print("Finished registering GUIDs...")


# Basic Authentication
class DiscussionForumBasicAuth(BasicAuth):
    def __init__(self, app=None):
        if app is not None:
            self.app = app
            self.init_app(app)
        else:
            self.app = None

    def check_credentials(self, username, password):
        if username != None and password != None:
            user = fetch_user(username)
            if user != None:
                if user[1] == username and check_password_hash(user[2], password):
                    return 'true'
                else:
                    return None
            else:
                return None
        else:
            return None


basic_auth = DiscussionForumBasicAuth(app)


def fetch_user(username):
    user = query_db('SELECT * FROM user WHERE username = ?', [username], one=True)
    return user


# create database connection
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        # db = g._database = sqlite3.connect(DATABASE)
        db = sqlite3.connect(DATABASE, detect_types=sqlite3.PARSE_DECLTYPES)
    return db


# close connection when not in use
@app.teardown_appcontext
def close_database(exception):
    """Closes the database again at the end of the request."""
    top = _app_ctx_stack.top
    if hasattr(top, 'sqlite_db'):
        top.sqlite_db.close()


def get_all_db():
    """Opens a new database connection to all the database shards."""
    connections = []
    for db in DATABASES:
        print(db)
        # connect = sqlite3.connect(app.config[db], detect_types=sqlite3.PARSE_DECLTYPES)
        connect = sqlite3.connect(db, detect_types=sqlite3.PARSE_DECLTYPES)
        connect.row_factory = sqlite3.Row
        connections.append(connect)
    return connections


# Get shard Database using the thread_id
def get_shard_db(thread_id):
    dbNumber = getdbnumber(thread_id)
    print(dbNumber)
    DATABASE = DATABASES[dbNumber]
    sqlite_db = 'sqlite_db' + str(dbNumber)
    print(DATABASE)
    top = _app_ctx_stack.top
    if not hasattr(top, sqlite_db):
        print("Going to create new instance")
        db = sqlite3.connect(DATABASE, detect_types=sqlite3.PARSE_DECLTYPES)
        print("done creating instance")
    else:
        print("Instance is already created")
    return db


# Create Schema for the shard databases
def create_schema():
    db = get_db()
    with app.open_resource('createSchema.sql', mode='r') as f:
        db.cursor().executescript(f.read())
        print(db)
    connections = get_all_db()
    for connect in connections:
        print(connect)
        with app.open_resource('createSchema1.sql', mode='r') as f:
            connect.cursor().executescript(f.read())


@app.cli.command('initdb')
def create_schema_command():
    """Initializes the database. and create schema"""
    create_schema()
    print('Database Schema Created')
    insert_data()
    print('Dummy data inserted to database')


# Insert dummy data into database
def insert_data():
    with app.app_context():
        with app.open_resource('insertData.sql', mode='r') as f:
            db = get_db()
            db.cursor().executescript(f.read())
            db.commit()
            db.close()
        with app.open_resource('insertData2.sql', 'r') as csvDataFile:
            csvReader = csv.reader(csvDataFile, delimiter='|')
            for line in csvReader:
                db = get_db()
                print(db);
                if "thread" in line[0]:
                    print("Add Thread Entry")
                    forum_id = line[2]

                    db.execute('''insert into thread (thread_id,forum_id, title) values (?, ?, ?)''',
                               (uuid.UUID(line[1]), int(forum_id), line[3]))
                    db.commit()
                    db.close()
                else:
                    print("None")

        with app.open_resource('insertData1.sql', 'r') as csvDataFile:
            csvReader = csv.reader(csvDataFile, delimiter='|')
            for line in csvReader:
                print("post insertion start.....")
                print(uuid.UUID(line[2]))
                db_number = getdbnumber(uuid.UUID(line[2]))
                dbs = get_all_db()
                print(dbs)
                db = dbs[db_number]
                print(db)
                if "post" in line[0]:
                    print("Add post table entry")
                    post_id = line[1];
                    db.execute('''insert into post (post_id,thread_id,user_id,text,timestamp) values (?, ?, ?,?,?)''',
                               [int(post_id), uuid.UUID(line[2]), int(line[3]), line[4], datetime.now()])
                    db.commit()
                    db.close()
                else:
                    print("None")


def getdbnumber(thread_id):
    """Convinient method to identify the database bucket based on the threadid."""
    dbNumber = int(int(thread_id) % 3)
    return dbNumber


###### Initial operations completed ####


# A factory class
def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


# common query function
def query_db(query, args=(), one=False):
    print(args)
    print(query)
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv


# Find user_id using username
def get_user_name(username):
    rv = query_db('SELECT username FROM user WHERE username = ?',
                  [username], one=True)
    return rv[0] if rv else None


# Return user_id using the user_id
def get_user_id(_id):
    rv = query_db('SELECT user_id FROM user WHERE user_id = ?',
                  [_id], one=True)
    return rv[0] if rv else None


# User registration
@app.route('/users', methods=['POST'])
def register_user():
    parser = reqparse.RequestParser()
    parser.add_argument('username',
                        type=str,
                        required=True,
                        help="This field cannot be blank.")
    parser.add_argument('password',
                        type=str,
                        required=True,
                        help="This field cannot be blank.")
    data = parser.parse_args()

    if get_user_name(data['username']):
        return jsonify({"message": "user with that name already exists"}), 409

    connection = get_db()
    cursor = connection.cursor()
    query = "INSERT INTO user VALUES (NULL,?,?)"
    cursor.execute(query, (data['username'], generate_password_hash(data['password'])))
    connection.commit()
    connection.close()
    resp = Response(status=201, mimetype='application/json')
    return resp


# Update User Info
@app.route('/users/<username>', methods=['PUT'])
@basic_auth.required
def update_user(username):
    parser = reqparse.RequestParser()
    parser.add_argument('username',
                        type=str,
                        required=True,
                        help="This field cannot be blank.")
    parser.add_argument('password',
                        type=str,
                        required=True,
                        help="This field cannot be blank.")
    data = parser.parse_args()
    if get_user_name(username) is None:
        return jsonify({"message": "user with that name not found"}), 404

    if request.authorization.username != username:
        return jsonify({"message": "not authenticated user"}), 409

    connection = get_db()
    cursor = connection.cursor()

    query = "update user set password = ? where username = ?"
    cursor.execute(query, (generate_password_hash(data['password']), username))

    connection.commit()
    connection.close()

    return jsonify({"message": "user updated successfully"}), 200


############################## Forum API's ##############################

# Find forumname based on name
def get_forum_name(name):
    rv = query_db('SELECT name FROM forum WHERE name = ?',
                  [name], one=True)
    return rv[0] if rv else None


# Find forum id
def get_forum_id():
    rv = query_db('SELECT forum_id FROM forum ORDER BY forum_id DESC',
                  one=True)
    return rv[0] if rv else None


# Find user id
def get_user_id(username):
    rv = query_db('SELECT user_id FROM user where username = ?', [username], one=True)
    return rv[0] if rv else None


# Find user_id using username
def get_forum_user_id(username):
    rv = query_db('SELECT user_id FROM user WHERE username = ?',
                  [username], one=True)
    return rv[0] if rv else None


# GET Operation on forums
@app.route('/forums', methods=['GET'])
def get_forum():
    forums = query_db('''
           SELECT f.forum_id as id, f.name as name, u.username as creator 
           FROM forum f, user u 
           where f.user_id = u.user_id limit ?''', [PER_PAGE])

    forumdic = []
    if forums:
        for forum in forums:
            forumdic.append({"id": forum[0], "name": forum[1], "creator": forum[2]})
        return jsonify({'Forums': forumdic}), 200
    return {}


# POST Operation on forums
@app.route('/forums', methods=['POST'])
@basic_auth.required
def post_forums():
    parser = reqparse.RequestParser()
    parser.add_argument('name',
                        type=str,
                        required=True,
                        help="This field cannot be blank.")
    data = parser.parse_args()
    connection = get_db()
    cursor = connection.cursor()
    user_id = get_user_id(request.authorization.username)
    if user_id is not None:
        if get_forum_name(data['name']):
            return jsonify({"message": "forum with that name already exists"}), 409
        query = "INSERT INTO forum VALUES (NULL,?,?)"
        cursor.execute(query, (data['name'], user_id))
    else:
        resp = Response(status=404, mimetype='application/json')
        connection.commit()
        return resp
    connection.commit()

    respObj = Response(status=201, mimetype='application/json')

    forum_id = get_forum_id()
    if forum_id:
        respObj.headers['Location'] = 'http://127.0.0.1:5000/forums/' + str(forum_id)
    connection.close()
    return respObj


############################## Thread API's ##############################

# Get forum_id for thread
def get_thread_forum_id(forumid):
    rv = query_db('SELECT forum_id FROM forum WHERE forum_id = ?',
                  [forumid], one=True)
    return rv[0] if rv else None


# Get thread Id
def get_thread_id(title):
    rv = query_db('SELECT thread_id FROM thread where title = ?', [title], one=True)
    return rv[0] if rv else None


# Find user_id using the username
def get_logged_in_user_id(username):
    if username is None:
        return None
    rv = query_db('SELECT user_id FROM user WHERE username = ?',
                  [username], one=True)
    return rv[0] if rv else None


# GET Operation on Thread
@app.route('/forums/<forum_id>', methods=['GET'])
def get_threads(forum_id):
    threads = query_db('''SELECT * from thread where forum_id = ? ''', [forum_id])
    print("in get")
    print(threads)
    threadlist = []
    if threads:
        for thread in threads:
            print("in thread")
            print(thread[0])
            thread_id = thread[0]
            posts = query_sharddb(uuid.UUID(str(thread_id)), '''select * from post where post_id = (SELECT min(post_id) from post
                                                            where thread_id=?)
                                                            UNION
                                                            select * from post where post_id = (SELECT max(post_id) from post
                                                            where thread_id=?)''',
                                  [thread_id,thread_id],one=False)
            print(posts)
            i=0;
            username=""
            timestamp=""
            for post in posts:
                timestamp = post[4]
                if(i==0):
                    users = query_db('''SELECT * from user where user_id = ? limit 1 ''', [post[2]])
                    for user in users:
                        username = user
                        print(username[1])
                else:
                    timestamp = post[4];
                    print(timestamp)
                i=i+1;
            threadlist.append({"id": thread_id, "title": thread[2], "creator": username[1], "timestamp": timestamp})
            print(threadlist)
        return jsonify({'Threads': threadlist}), 200
    else:
        print("in else get thread")
        return jsonify({"message": "forum id not found"}), 404


# POST Operation in Thread

@app.route('/forums/<forum_id>', methods=['POST'])
@basic_auth.required
def post_threads(forum_id):
    # parser to parse the payload
    parser = reqparse.RequestParser()
    parser.add_argument('title',
                        type=str,
                        required=True,
                        help="This field cannot be blank.")
    parser.add_argument('text',
                        type=str,
                        required=True,
                        help="This field cannot be blank.")

    data = parser.parse_args()

    if get_thread_forum_id(forum_id) is None:
        return jsonify({"message": "forum does not exist"}), 404

    db = get_db()
    thread_id = uuid.uuid4()
    print("before inserting in thread")
    print(thread_id)
    #
    # db.execute('''insert into thread (thread_id,forum_id, title) values (?, ?, ?)''',
    #            (uuid.UUID(thread_id), int(forum_id), data['title']))
    db.execute('''insert into thread (thread_id,forum_id, title) values (?, ?, ?)''',
               (uuid.UUID(str(thread_id)), int(forum_id), data['title']))
    db.commit()
    db.close()
    print("done inserting in thread")
    # thread_id = get_thread_id(data['title'])
    user_id = get_user_id(request.authorization.username)
    if thread_id and user_id:
        db1 = get_shard_db(thread_id)
        print("post insertion begins")
        print(db)
        query = "INSERT INTO post VALUES (?,?,?,?,?)"
        db1.execute('''INSERT INTO post(thread_id, user_id, text, timestamp) VALUES (?,?,?,?)''',
                    (uuid.UUID(str(thread_id)), user_id, data['text'], datetime.now()))
        db1.commit()
        db1.close()
        print("done post insertion")
        resp = Response(status=201, mimetype='application/json')
        resp.headers['Location'] = 'http://127.0.0.1:5000/forums/' + str(forum_id) + '/' + str(thread_id)

    return resp


############################## POST API's ##############################

# Get thread Id using forum Id
def get_post_thread_id(forum_id, thread_id):
    print(thread_id)
    print("get post thread_id method second line")
    print(uuid.UUID(thread_id))
    rv = query_db('SELECT thread_id FROM thread WHERE thread_id = ? and forum_id = ?',
                  [uuid.UUID(str(thread_id)), forum_id], one=True)
    print("done querying")
    #print(rv[0])
    return rv[0] if rv else None


# Find user_id using the username
def get_logged_in_user_id(username):
    rv = query_db('SELECT user_id FROM user WHERE username = ?',
                  [username], one=True)
    return rv[0] if rv else None


def query_sharddb(thid, query, args=(), one=False):
    """Queries the database and returns a list of dictionaries."""
    cur = get_shard_db(thid).execute(query, args)
    rv = cur.fetchall()
    return (rv[0] if rv else None) if one else rv


# GET operations for POST'S
@app.route('/forums/<forum_id>/<thread_id>', methods=['GET'])
def get_posts(forum_id, thread_id):
    print('inside method')
    # if get_post_thread_id(forum_id, thread_id) is None:
    #     return jsonify({"message":"forum / thread does not exist"}), 404

    threads = query_db('''SELECT * from thread where thread_id = ? and forum_id = ?''', [uuid.UUID(str(thread_id)), forum_id])
    posts = query_sharddb(uuid.UUID(thread_id), '''select * from post where thread_id = ?''', [uuid.UUID(str(thread_id))],one=False)
    print("in get post")
    print(posts)
    print(threads)
    # posts = query_db('''SELECT * FROM POST
    #                 SELECT u.username as author, p.text, p.timestamp
    #                 FROM post p, thread t, user u
    #                 where t.thread_id = p.thread_id
    #                 and t.thread_id = ? and t.forum_id = ?
    #                 and u.user_id  = p.user_id
    #                 order by timestamp desc''', [thread_id, forum_id])

    postlist = []
    if posts and threads:
        for post in posts:
            users = query_db('''SELECT username from user where user_id = ?''', [post[2]], one=True)
            for user in users:
                postlist.append({"author": user, "text": post[3], "timestamp": post[4]})
        return jsonify({'Posts': postlist}), 200
    else:
        print("in else get thread")
        return jsonify({"message": "forum id/thread_id not found"}), 404


# POST operations for POST'S
@app.route('/forums/<forum_id>/<thread_id>', methods=['POST'])
@basic_auth.required
def post_posts(forum_id, thread_id):
    parser = reqparse.RequestParser()
    parser.add_argument('text',
                        type=str,
                        required=True,
                        help="This field cannot be blank.")
    data = parser.parse_args()

    if get_post_thread_id(forum_id, thread_id) is None:
        return jsonify({"message": "forum / thread does not exist"}), 404
    user_id = get_user_id(request.authorization.username)
    if thread_id and user_id:
        db = get_shard_db(uuid.UUID(thread_id))
        query = "INSERT INTO post VALUES (?,?,?,?,?)"
        db.execute('''INSERT INTO post(thread_id, user_id, text, timestamp) VALUES (?,?,?,?)''',
                   [uuid.UUID(str(thread_id)), user_id, data['text'], datetime.now()])
        db.commit()
        db.close()

        resp = Response(status=201, mimetype='application/json')
        resp.headers['Location'] = 'http://127.0.0.1:5000/forums/' + str(forum_id) + '/' + str(thread_id)

    return resp


if __name__ == '__main__':
    app.run()


CREATE KEYSPACE IF NOT EXISTS discussionforum WITH replication = {'class': 'SimpleStrategy', 'replication_factor' : 1};
CREATE TABLE IF NOT EXISTS discussionforum.user(user_id uuid, username text, password text, PRIMARY KEY (user_id));
CREATE INDEX ON discussionforum.user(username);
CREATE TABLE IF NOT EXISTS discussionforum.forum(forum_id uuid, name text, creator text, PRIMARY KEY (forum_id));
CREATE INDEX ON discussionforum.forum(name);
CREATE TABLE IF NOT EXISTS discussionforum.thread_post(thread_id uuid, forum_id uuid, title text, creator text, timestamp timestamp, posts list<text>, PRIMARY KEY (thread_id, forum_id));
CREATE INDEX ON discussionforum.thread_post(title);
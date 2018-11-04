drop table if exists user;
create table user (
  user_id integer primary key autoincrement,
  username text not null,
  password text not null
);

drop table if exists forum;
create table forum (
  forum_id integer primary key autoincrement,
  name text not null,
  user_id integer not null,
  FOREIGN KEY(user_id) REFERENCES user(user_id)
);

drop table if exists thread;
create table thread (
  thread_id GUID primary key,
  forum_id integer not null,
  title text not null,
  FOREIGN KEY(forum_id) REFERENCES forum(forum_id)
);



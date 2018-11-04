drop table if exists post;
create table post (
  post_id integer primary key autoincrement,
  thread_id GUID not null,
  user_id integer not null,
  text text not null,
  timestamp DateTime not null
);
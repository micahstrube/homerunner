drop table if exists users;
create table users (
  id integer primary key autoincrement,
  google_id text not null
);
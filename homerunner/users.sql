drop table if exists users;
create table users (
  id integer primary key autoincrement,
  google_id text not null,
  email text not null,
  name text not null,
  picture_url text not null,
  receive_email integer not null default 0
);
drop table if exists teams;
create table teams (
  id integer primary key autoincrement,
  name text not null,
  score integer not null default 0
)

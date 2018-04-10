drop table if exists all_players;
create table all_players (
  id integer primary key autoincrement,
  player text not null,
  home_runs integer not null default 0
);

drop table if exists players;
create table players (
  id integer primary key autoincrement,
  name text not null,
  team_id integer not null,
  home_runs integer not null default 0,
  is_substitute integer default 0,
  foreign key(team_id) references teams(id)
);

drop table if exists teams;
create table teams (
  id integer primary key autoincrement,
  name text not null,
  score integer not null default 0
)
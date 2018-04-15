drop table if exists players;
create table players (
  id integer primary key autoincrement,
  name text not null,
  last_game_id text,
  home_runs integer not null default 0,
  is_substitute integer default 0,
  team_id integer,
  foreign key(team_id) references teams(id)
);

drop table if exists teams;
create table teams (
  id integer primary key autoincrement,
  name text not null,
  score integer not null default 0
)
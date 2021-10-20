create user sdh password 'sdh';
create database sdh_db with owner sdh;
grant connect, create, temporary on database sdh_db to sdh;

-- \connect sdh_db sdh


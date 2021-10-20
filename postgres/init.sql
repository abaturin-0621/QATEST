create user qa password 'qa';
create database qa_db with owner qa;
grant connect, create, temporary on database qa_db to qa;




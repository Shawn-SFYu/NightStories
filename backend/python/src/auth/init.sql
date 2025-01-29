CREATE USER 'auth_user'@'localhost' IDENTIFIED BY 'auth_password_123';

CREATE DATABASE auth;

GRANT ALL PRIVILEGES ON auth.* TO 'auth_user'@'localhost';

USE auth;

CREATE TABLE users (
    id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL
);

INSERT INTO users (email, password) VALUES ('shawn.sf.yuan@gmail.com', 'shawn-adamin');
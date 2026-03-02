CREATE DATABASE tour_planner;
USE tour_planner;

CREATE TABLE destinations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    state VARCHAR(50),
    name VARCHAR(100),
    hotel_cost FLOAT,
    food_cost FLOAT,
    sightseeing_cost FLOAT,
    image_url VARCHAR(255)
);

CREATE TABLE cars (
    id INT AUTO_INCREMENT PRIMARY KEY,
    car_name VARCHAR(100),
    price_per_day FLOAT
);

CREATE TABLE bookings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    destination_id INT,
    car_id INT,
    days INT,
    persons INT,
    total_budget FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
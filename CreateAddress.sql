CREATE TABLE IF NOT EXISTS crime_address(
    address_key SERIAL PRIMARY KEY,
    address VARCHAR(50),
    place VARCHAR(50),
    latitude DECIMAL(9,6),
    longitude DECIMAL(9,6)
);
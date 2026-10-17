#!/bin/bash
set -e

echo "Running local PostgreSQL initialization script..."

# Function to create user and database if not exists
create_user_and_database() {
    local database=$1
    echo "Creating database '$database'..."
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
        SELECT 'CREATE DATABASE $database'
        WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$database')\gexec
        GRANT ALL PRIVILEGES ON DATABASE $database TO $POSTGRES_USER;
EOSQL
}

create_user_and_database "user_service"
create_user_and_database "product_service"
create_user_and_database "order_service"
create_user_and_database "payment_service"

echo "All microservice databases initialized successfully!"

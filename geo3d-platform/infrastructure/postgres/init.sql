-- Geo3D Platform — PostGIS Database Initialization
-- Run by Docker entrypoint on first start

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS postgis_topology;

-- Create spatial indexes helper function
-- (Tables are created by SQLAlchemy on application startup)

-- Seed: default project for development
-- (Commented out — let the API handle creation)

SELECT postgis_version();
SELECT 'PostGIS initialization complete.' AS status;

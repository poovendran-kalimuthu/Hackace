-- ============================================================
-- KPR Hackace — Database Setup Script
-- Run once: mysql -u root -p < database/setup.sql
-- ============================================================

-- Create the database
CREATE DATABASE IF NOT EXISTS Hackace
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE Hackace;

-- ── Example table (replace with your actual schema) ──────────
CREATE TABLE IF NOT EXISTS items (
  id          INT UNSIGNED     NOT NULL AUTO_INCREMENT,
  name        VARCHAR(255)     NOT NULL,
  description TEXT,
  created_at  DATETIME         NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at  DATETIME         NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ── Optional seed data ────────────────────────────────────────
INSERT INTO items (name, description) VALUES
  ('Sample Item 1', 'First test record'),
  ('Sample Item 2', 'Second test record');

const mysql = require('mysql2/promise');
require('dotenv').config();

// Create a connection pool — reuses connections instead of opening/closing each time
const pool = mysql.createPool({
  host:     process.env.DB_HOST     || 'localhost',
  port:     parseInt(process.env.DB_PORT) || 3306,
  user:     process.env.DB_USER     || 'root',
  password: process.env.DB_PASSWORD || '',
  database: process.env.DB_NAME     || 'kpr_hackace',
  waitForConnections: true,
  connectionLimit:    10,
  queueLimit:         0,
});

/**
 * Execute a parameterised SQL query.
 * @param {string} sql        - SQL string with ? placeholders
 * @param {Array}  [params]   - Values to bind
 * @returns {Promise<Array>}  - Result rows
 */
async function query(sql, params = []) {
  const [rows] = await pool.execute(sql, params);
  return rows;
}

module.exports = { pool, query };

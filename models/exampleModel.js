const { query } = require('../config/db');

/**
 * Example model — demonstrates the raw-SQL pattern.
 * Replace / extend with your actual domain tables.
 */

/** Fetch all items */
async function findAll() {
  return query('SELECT * FROM items ORDER BY created_at DESC');
}

/** Fetch a single item by ID */
async function findById(id) {
  const rows = await query('SELECT * FROM items WHERE id = ?', [id]);
  return rows[0] || null;
}

/** Create a new item */
async function create({ name, description }) {
  const result = await query(
    'INSERT INTO items (name, description) VALUES (?, ?)',
    [name, description]
  );
  return findById(result.insertId);
}

/** Update an existing item */
async function update(id, { name, description }) {
  await query(
    'UPDATE items SET name = ?, description = ? WHERE id = ?',
    [name, description, id]
  );
  return findById(id);
}

/** Delete an item */
async function remove(id) {
  const result = await query('DELETE FROM items WHERE id = ?', [id]);
  return result.affectedRows > 0;
}

module.exports = { findAll, findById, create, update, remove };

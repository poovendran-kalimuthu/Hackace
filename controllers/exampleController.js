const Item = require('../models/exampleModel');

/**
 * GET /api/items
 * Returns all items.
 */
async function getAll(req, res, next) {
  try {
    const items = await Item.findAll();
    res.json({ success: true, data: items });
  } catch (err) {
    next(err);
  }
}

/**
 * GET /api/items/:id
 * Returns a single item.
 */
async function getOne(req, res, next) {
  try {
    const item = await Item.findById(req.params.id);
    if (!item) {
      const err = new Error('Item not found');
      err.statusCode = 404;
      return next(err);
    }
    res.json({ success: true, data: item });
  } catch (err) {
    next(err);
  }
}

/**
 * POST /api/items
 * Body: { name, description }
 * Creates and returns the new item.
 */
async function create(req, res, next) {
  try {
    const { name, description } = req.body;
    if (!name) {
      const err = new Error('Field "name" is required');
      err.statusCode = 400;
      return next(err);
    }
    const item = await Item.create({ name, description });
    res.status(201).json({ success: true, data: item });
  } catch (err) {
    next(err);
  }
}

/**
 * PUT /api/items/:id
 * Body: { name, description }
 * Updates and returns the updated item.
 */
async function update(req, res, next) {
  try {
    const { name, description } = req.body;
    const existing = await Item.findById(req.params.id);
    if (!existing) {
      const err = new Error('Item not found');
      err.statusCode = 404;
      return next(err);
    }
    const item = await Item.update(req.params.id, { name, description });
    res.json({ success: true, data: item });
  } catch (err) {
    next(err);
  }
}

/**
 * DELETE /api/items/:id
 * Deletes an item and returns 204 No Content.
 */
async function remove(req, res, next) {
  try {
    const deleted = await Item.remove(req.params.id);
    if (!deleted) {
      const err = new Error('Item not found');
      err.statusCode = 404;
      return next(err);
    }
    res.status(204).send();
  } catch (err) {
    next(err);
  }
}

module.exports = { getAll, getOne, create, update, remove };

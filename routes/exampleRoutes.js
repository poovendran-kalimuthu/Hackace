const express = require('express');
const router  = express.Router();
const ctrl    = require('../controllers/exampleController');

// GET    /api/items
router.get('/',       ctrl.getAll);

// GET    /api/items/:id
router.get('/:id',    ctrl.getOne);

// POST   /api/items
router.post('/',      ctrl.create);

// PUT    /api/items/:id
router.put('/:id',    ctrl.update);

// DELETE /api/items/:id
router.delete('/:id', ctrl.remove);

module.exports = router;

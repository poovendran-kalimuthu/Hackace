require('dotenv').config();

const express      = require('express');
const cors         = require('cors');
const logger       = require('./middleware/logger');
const errorHandler = require('./middleware/errorHandler');
const { pool }     = require('./config/db');

// ── Routes ───────────────────────────────────────────────────────────────────
const exampleRoutes = require('./routes/exampleRoutes');
// Add more route imports here as you build out the project:
// const userRoutes = require('./routes/userRoutes');

// ── App setup ────────────────────────────────────────────────────────────────
const app  = express();
const PORT = process.env.PORT || 5001;

// ── Middleware ────────────────────────────────────────────────────────────────
app.use(cors());                        // Allow all origins (Python GUI, Postman, etc.)
app.use(express.json());                // Parse JSON request bodies
app.use(express.urlencoded({ extended: true })); // Parse form-encoded bodies
app.use(logger);                        // HTTP request logging

// ── Health check ─────────────────────────────────────────────────────────────
app.get('/api/health', (req, res) => {
  res.json({ success: true, status: 'ok', timestamp: new Date().toISOString() });
});

// ── API Routes ────────────────────────────────────────────────────────────────
app.use('/api/items', exampleRoutes);
// Mount more routes here:
// app.use('/api/users', userRoutes);

// ── 404 handler ───────────────────────────────────────────────────────────────
app.use((req, res) => {
  res.status(404).json({ success: false, error: `Route not found: ${req.method} ${req.originalUrl}` });
});

// ── Global error handler (must be last) ──────────────────────────────────────
app.use(errorHandler);

// ── Start server ──────────────────────────────────────────────────────────────
async function start() {
  try {
    // Verify DB connection before accepting requests
    await pool.query('SELECT 1');
    console.log('✅ MySQL connected successfully');

    app.listen(PORT, () => {
      console.log(`🚀 Server running on http://localhost:${PORT}`);
      console.log(`   Health: http://localhost:${PORT}/api/health`);
      console.log(`   Items:  http://localhost:${PORT}/api/items`);
    });
  } catch (err) {
    console.error('❌ Failed to connect to MySQL:', err.message);
    console.error('   Check your .env credentials and ensure MySQL is running.');
    process.exit(1);
  }
}

start();

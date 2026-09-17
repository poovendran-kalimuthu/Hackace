const morgan = require('morgan');

// 'dev' format: METHOD URL STATUS response-time ms - content-length
const logger = morgan('dev');

module.exports = logger;

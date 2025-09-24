// Platform registry
// Side-effect import: starts the Upwork pipeline scheduler
require('./upwork/fetcher');

// Re-export token refresh for scheduler in index.js
const refreshToken = require('./upwork/tokenManager');

module.exports = { refreshToken };



const jwt = require('jsonwebtoken');

module.exports = function auth(req, res, next) {
  try {
    const hdr = req.headers['authorization'] || '';
    const m = hdr.match(/^Bearer\s+(.+)$/i);
    if (!m) return res.status(401).json({ error: 'Missing Authorization header' });
    const token = m[1];
    const secret = process.env.JWT_SECRET || 'your_jwt_secret';
    const payload = jwt.verify(token, secret);
    if (!payload || !payload.id || !payload.company_id) {
      return res.status(401).json({ error: 'Invalid token' });
    }
    req.user = { id: payload.id, company_id: payload.company_id };
    next();
  } catch (err) {
    return res.status(401).json({ error: 'Unauthorized' });
  }
};



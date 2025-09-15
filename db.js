
const { Client } = require('pg');
require('dotenv').config();

const useSSL = String(process.env.DB_SSL || '').toLowerCase() === 'true';

const client = new Client({
  host: process.env.DB_HOST,
  port: process.env.DB_PORT,
  user: process.env.DB_USER,
  password: process.env.DB_PASSWORD,
  database: process.env.DB_NAME,
  ssl: useSSL ? { rejectUnauthorized: false } : false,
});

console.log(`DB SSL: ${useSSL ? 'enabled' : 'disabled'}`);

client.connect()
  .then(() => console.log('Connected to PostgreSQL'))
  .catch(err => console.error('DB connection error', err.stack));

module.exports = client;

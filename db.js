
const { Client } = require('pg');
require('dotenv').config();

const client = new Client({
  host: process.env.DB_HOST,
  port: process.env.DB_PORT,
  user: process.env.DB_USER,
  password: process.env.DB_PASSWORD,
  database: process.env.DB_NAME,
  ssl: {
        rejectUnauthorized: false, // Disable SSL validation (use cautiously)
      },
});

// const client = new Client({
//       host: "122.176.158.168",
//       port: 5432,
//       user: "profile",
//       password: "profileUYh$13#",
//       database: "profiledb",
//       ssl: {
//         rejectUnauthorized: false, // Disable SSL validation (use cautiously)
//       },
//     });
 

client.connect()
  .then(() => console.log('Connected to PostgreSQL'))
  .catch(err => console.error('DB connection error', err.stack));

module.exports = client;

const axios = require('axios');
const fs = require('fs').promises;
const path = require('path');
const dotenv = require('dotenv');

dotenv.config();

const AUTH_URL = 'https://www.upwork.com/ab/account-security/oauth2/authorize';
const TOKEN_URL = 'https://www.upwork.com/api/v3/oauth2/token';

function requireCreds(keys) {
  const missing = keys.filter(k => !process.env[k]);
  if (missing.length) throw new Error(`Missing env vars: ${missing.join(', ')}`);
}

async function writeEnv(updates) {
  const envPath = path.resolve(__dirname, '../../.env');
  let content = '';
  try { content = await fs.readFile(envPath, 'utf8'); } catch (_) { content = ''; }
  const setLine = (c, key, value) => {
    const regex = new RegExp(`^${key}=.*$`, 'm');
    if (regex.test(c)) return c.replace(regex, `${key}=${value}`);
    const suffix = c.endsWith('\n') || c.length === 0 ? '' : '\n';
    return c + suffix + `${key}=${value}\n`;
  };
  if (updates.ACCESS_TOKEN) content = setLine(content, 'ACCESS_TOKEN', updates.ACCESS_TOKEN);
  if (updates.REFRESH_TOKEN) content = setLine(content, 'REFRESH_TOKEN', updates.REFRESH_TOKEN);
  if (updates.ACCESS_TOKEN_ISSUED_AT) content = setLine(content, 'ACCESS_TOKEN_ISSUED_AT', updates.ACCESS_TOKEN_ISSUED_AT);
  await fs.writeFile(envPath, content, 'utf8');
}

async function refreshWithExisting() {
  requireCreds(['CLIENT_ID', 'CLIENT_SECRET', 'REFRESH_TOKEN']);
  const body = new URLSearchParams({
    grant_type: 'refresh_token',
    refresh_token: process.env.REFRESH_TOKEN,
    client_id: process.env.CLIENT_ID,
    client_secret: process.env.CLIENT_SECRET
  }).toString();
  const { data } = await axios.post(TOKEN_URL, body, { headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, timeout: 15000 });
  await writeEnv({ ACCESS_TOKEN: data.access_token, REFRESH_TOKEN: data.refresh_token, ACCESS_TOKEN_ISSUED_AT: new Date().toISOString() });
  console.log('✅ Refreshed tokens written to .env');
}

async function exchangeAuthCodeForTokens() {
  requireCreds(['CLIENT_ID', 'CLIENT_SECRET', 'REDIRECT_URI', 'AUTH_CODE']);
  const body = new URLSearchParams({
    grant_type: 'authorization_code',
    code: process.env.AUTH_CODE,
    client_id: process.env.CLIENT_ID,
    client_secret: process.env.CLIENT_SECRET,
    redirect_uri: process.env.REDIRECT_URI
  }).toString();
  const { data } = await axios.post(TOKEN_URL, body, { headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, timeout: 15000 });
  await writeEnv({ ACCESS_TOKEN: data.access_token, REFRESH_TOKEN: data.refresh_token, ACCESS_TOKEN_ISSUED_AT: new Date().toISOString() });
  console.log('✅ Exchanged auth code for tokens and saved to .env');
}

function printAuthUrl() {
  requireCreds(['CLIENT_ID']);
  const redirect = process.env.REDIRECT_URI || 'http://localhost:3009/callback';
  const scopes = process.env.UPWORK_SCOPES || 'public_profile';
  const url = `${AUTH_URL}?client_id=${process.env.CLIENT_ID}&redirect_uri=${encodeURIComponent(redirect)}&response_type=code&scope=${encodeURIComponent(scopes)}`;
  console.log(url);
}

async function main() {
  const arg = process.argv[2] || '';
  if (arg === '--auth-url') return printAuthUrl();
  if (arg === '--exchange') return exchangeAuthCodeForTokens();
  if (arg === '--refresh') return refreshWithExisting();

  // Auto mode: prefer refresh; fallback to exchange; else print URL
  if (process.env.REFRESH_TOKEN) return refreshWithExisting();
  if (process.env.AUTH_CODE) return exchangeAuthCodeForTokens();
  return printAuthUrl();
}

main().catch(err => { console.error('❌', err.message); process.exit(1); });
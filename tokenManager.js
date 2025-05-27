const fs = require('fs');
const path = require('path');
const dotenv = require('dotenv');
const axios = require('axios');

dotenv.config(); // Load current env values

const refreshToken = async () => {
  try {
    const response = await axios.post('https://www.upwork.com/api/v3/oauth2/token', null, {
          params: {
            grant_type: 'refresh_token',
            refresh_token: process.env.REFRESH_TOKEN,
            client_id: process.env.CLIENT_ID,
            client_secret: process.env.CLIENT_SECRET
          },
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded'
          }
        });

    const newAccessToken = response.data.access_token;
    const newRefreshToken = response.data.refresh_token;

    // console.log('✅ Refreshed Access Token:', newAccessToken);

    // Update .env file
    const envPath = path.resolve(__dirname, '.env');
    let envContent = fs.readFileSync(envPath, 'utf8');

    envContent = envContent
      .replace(/ACCESS_TOKEN=.*/g, `ACCESS_TOKEN=${newAccessToken}`)
      .replace(/REFRESH_TOKEN=.*/g, `REFRESH_TOKEN=${newRefreshToken}`);

    fs.writeFileSync(envPath, envContent);
    console.log('🔄 .env updated with new tokens');

    return newAccessToken;

  } catch (error) {
    console.error('❌ Token refresh failed:', error.response?.data || error.message);
    return null;
  }
};

module.exports = refreshToken;

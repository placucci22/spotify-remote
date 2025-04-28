const express = require('express');
const axios = require('axios');
const querystring = require('querystring');
const dotenv = require('dotenv');

dotenv.config();

const app = express();
const PORT = process.env.PORT || 3000;

const client_id = process.env.CLIENT_ID;
const client_secret = process.env.CLIENT_SECRET;
const redirect_uri = process.env.REDIRECT_URI;

let access_token = '';
let refresh_token = '';

app.get('/', (req, res) => {
  res.send('Server running!');
});

app.get('/login', (req, res) => {
  const scope = 'user-read-private user-read-email user-modify-playback-state user-read-playback-state streaming app-remote-control playlist-read-private playlist-read-collaborative';

  const queryParams = querystring.stringify({
    response_type: 'code',
    client_id: client_id,
    scope: scope,
    redirect_uri: redirect_uri,
  });

  res.redirect(`https://accounts.spotify.com/authorize?${queryParams}`);
});

app.get('/callback', async (req, res) => {
  const code = req.query.code || null;

  try {
    const response = await axios.post('https://accounts.spotify.com/api/token',
      querystring.stringify({
        grant_type: 'authorization_code',
        code: code,
        redirect_uri: redirect_uri,
      }),
      {
        headers: {
          'Authorization': 'Basic ' + Buffer.from(client_id + ':' + client_secret).toString('base64'),
          'Content-Type': 'application/x-www-form-urlencoded'
        }
      }
    );

    access_token = response.data.access_token;
    refresh_token = response.data.refresh_token;

    res.send('Login successful! You can now close this window.');
  } catch (error) {
    console.error('Error getting tokens:', error.response ? error.response.data : error.message);
    res.send('Error during authentication.');
  }
});

app.get('/refresh_token', async (req, res) => {
  try {
    const response = await axios.post('https://accounts.spotify.com/api/token',
      querystring.stringify({
        grant_type: 'refresh_token',
        refresh_token: refresh_token,
      }),
      {
        headers: {
          'Authorization': 'Basic ' + Buffer.from(client_id + ':' + client_secret).toString('base64'),
          'Content-Type': 'application/x-www-form-urlencoded'
        }
      }
    );

    access_token = response.data.access_token;
    res.json({ access_token: access_token });
  } catch (error) {
    console.error('Error refreshing token:', error.response ? error.response.data : error.message);
    res.send('Error refreshing token.');
  }
});

app.listen(PORT, () => {
  console.log(`Server is running on port ${PORT}`);
});
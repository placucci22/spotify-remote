{\rtf1\ansi\ansicpg1252\cocoartf2821
\cocoatextscaling0\cocoaplatform0{\fonttbl\f0\fswiss\fcharset0 Helvetica;}
{\colortbl;\red255\green255\blue255;}
{\*\expandedcolortbl;;}
\paperw11900\paperh16840\margl1440\margr1440\vieww11520\viewh8400\viewkind0
\pard\tx720\tx1440\tx2160\tx2880\tx3600\tx4320\tx5040\tx5760\tx6480\tx7200\tx7920\tx8640\pardirnatural\partightenfactor0

\f0\fs24 \cf0 const express = require('express');\
const dotenv = require('dotenv');\
const axios = require('axios');\
const querystring = require('querystring');\
\
dotenv.config();\
\
const app = express();\
const PORT = process.env.PORT || 3000; //\
\
\'d3timo, vou te passar **direto** o que voc\'ea precisa:  \
**Um `index.js` completo, limpo, funcionando para Railway e Spotify.**\
\
Aqui est\'e1:\
\
---\
\
# \uc0\u55357 \u56540  `index.js` (copia exatamente assim)\
\
```javascript\
const express = require('express');\
const axios = require('axios');\
const querystring = require('querystring');\
const dotenv = require('dotenv');\
\
dotenv.config();\
\
const app = express();\
const PORT = process.env.PORT || 3000;\
\
const client_id = process.env.CLIENT_ID;\
const client_secret = process.env.CLIENT_SECRET;\
const redirect_uri = process.env.REDIRECT_URI;\
\
let access_token = '';\
let refresh_token = '';\
\
app.get('/', (req, res) => \{\
  res.send('Server running!');\
\});\
\
app.get('/login', (req, res) => \{\
  const scope = 'user-read-private user-read-email user-modify-playback-state user-read-playback-state streaming app-remote-control playlist-read-private playlist-read-collaborative';\
\
  const queryParams = querystring.stringify(\{\
    response_type: 'code',\
    client_id: client_id,\
    scope: scope,\
    redirect_uri: redirect_uri,\
  \});\
\
  res.redirect(`https://accounts.spotify.com/authorize?$\{queryParams\}`);\
\});\
\
app.get('/callback', async (req, res) => \{\
  const code = req.query.code || null;\
\
  try \{\
    const response = await axios.post('https://accounts.spotify.com/api/token',\
      querystring.stringify(\{\
        grant_type: 'authorization_code',\
        code: code,\
        redirect_uri: redirect_uri,\
      \}),\
      \{\
        headers: \{\
          'Authorization': 'Basic ' + Buffer.from(client_id + ':' + client_secret).toString('base64'),\
          'Content-Type': 'application/x-www-form-urlencoded'\
        \}\
      \}\
    );\
\
    access_token = response.data.access_token;\
    refresh_token = response.data.refresh_token;\
\
    res.send('Login successful! You can now close this window.');\
  \} catch (error) \{\
    console.error('Error getting tokens:', error.response ? error.response.data : error.message);\
    res.send('Error during authentication.');\
  \}\
\});\
\
app.get('/refresh_token', async (req, res) => \{\
  try \{\
    const response = await axios.post('https://accounts.spotify.com/api/token',\
      querystring.stringify(\{\
        grant_type: 'refresh_token',\
        refresh_token: refresh_token,\
      \}),\
      \{\
        headers: \{\
          'Authorization': 'Basic ' + Buffer.from(client_id + ':' + client_secret).toString('base64'),\
          'Content-Type': 'application/x-www-form-urlencoded'\
        \}\
      \}\
    );\
\
    access_token = response.data.access_token;\
    res.json(\{ access_token: access_token \});\
  \} catch (error) \{\
    console.error('Error refreshing token:', error.response ? error.response.data : error.message);\
    res.send('Error refreshing token.');\
  \}\
\});\
\
app.listen(PORT, () => \{\
  console.log(`Server is running on port $\{PORT\}`);\
\});}
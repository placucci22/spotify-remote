{\rtf1\ansi\ansicpg1252\cocoartf2821
\cocoatextscaling0\cocoaplatform0{\fonttbl\f0\fswiss\fcharset0 Helvetica;}
{\colortbl;\red255\green255\blue255;}
{\*\expandedcolortbl;;}
\paperw11900\paperh16840\margl1440\margr1440\vieww11520\viewh8400\viewkind0
\pard\tx720\tx1440\tx2160\tx2880\tx3600\tx4320\tx5040\tx5760\tx6480\tx7200\tx7920\tx8640\pardirnatural\partightenfactor0

\f0\fs24 \cf0 const express = require('express');\
const axios = require('axios');\
const querystring = require('querystring');\
require('dotenv').config();\
\
const app = express();\
const port = process.env.PORT || 3000;\
\
// LOGIN\
app.get('/login', (req, res) => \{\
  const params = querystring.stringify(\{\
    response_type: 'code',\
    client_id: process.env.CLIENT_ID,\
    scope: 'user-read-playback-state user-modify-playback-state streaming app-remote-control',\
    redirect_uri: process.env.REDIRECT_URI\
  \});\
  res.redirect(`https://accounts.spotify.com/authorize?$\{params\}`);\
\});\
\
// CALLBACK\
app.get('/callback', async (req, res) => \{\
  const code = req.query.code || null;\
  const authOptions = \{\
    method: 'post',\
    url: 'https://accounts.spotify.com/api/token',\
    data: querystring.stringify(\{\
      code: code,\
      redirect_uri: process.env.REDIRECT_URI,\
      grant_type: 'authorization_code'\
    \}),\
    headers: \{\
      'Authorization': 'Basic ' + Buffer.from(process.env.CLIENT_ID + ':' + process.env.CLIENT_SECRET).toString('base64'),\
      'Content-Type': 'application/x-www-form-urlencoded'\
    \}\
  \};\
\
  try \{\
    const response = await axios(authOptions);\
    const \{ access_token, refresh_token \} = response.data;\
\
    global.access_token = access_token;\
    global.refresh_token = refresh_token;\
\
    res.send('Login efetuado com sucesso! Agora pode usar os comandos.');\
  \} catch (error) \{\
    res.send('Erro ao autenticar: ' + error.message);\
  \}\
\});\
\
// PLAYLIST 1\
app.get('/play/1', async (req, res) => \{\
  if (!global.access_token) return res.send('Token inexistente. Fa\'e7a login primeiro.');\
\
  try \{\
    await axios(\{\
      method: 'put',\
      url: 'https://api.spotify.com/v1/me/player/play',\
      headers: \{ 'Authorization': 'Bearer ' + global.access_token \},\
      data: \{ context_uri: 'spotify:playlist:37i9dQZF1E3904HjfoXYQz' \}\
    \});\
    res.send('Tocando playlist 1.');\
  \} catch (error) \{\
    res.send('Erro ao tocar: ' + error.message);\
  \}\
\});\
\
app.listen(port, () => \{\
  console.log(`Servidor rodando na porta $\{port\}`);\
\});}
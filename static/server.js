const https = require('https');
const fs = require('fs');
const express = require('express');
const WebSocket = require('ws');
const path = require('path');
const { db, collection, getDocs } = require("./firebase");

// SSL sertifikaları yükleme
const serverOptions = {
  key: fs.readFileSync('server.key'), // anahtar yolu
  cert: fs.readFileSync('server.cert') // sertifika yolu
};

const app = express();
// public klasöründeki dosyaları sttaik olarak sunarak.
app.use(express.static(path.join(__dirname, 'public')));

// HTTPS sunucusu kurma
const httpsServer = https.createServer(serverOptions, app);
// HTTPS sunucusunun üstünde WebSocket sunucusu oluştur
const wss = new WebSocket.Server({ noServer: true });

const users = {};
// Bağlanan kullanıcıların numaralarını tutmak için bir set
const connectedUserIDs = new Set(); 

async function getUsersFromFirebase() {
    const usersCollection = collection(db, 'users');
    const snapshot = await getDocs(usersCollection);
    // telefonNo'yu alıyoruz
    const users = snapshot.docs.map(doc => doc.data().telefonNo); 
    return users;
}  

// bir kullanıcı bağlandığında veya bağlantısı kesildiğinde kullanıcı listesini güncelle ve herkese duyur.
async function broadcastUserList() {
  const userList = Object.keys(users);
  const message = JSON.stringify({ type: "user-list", users: userList });
  wss.clients.forEach(client => {
    if (client.readyState === WebSocket.OPEN) {
      client.send(message);
    }
  });
}

wss.on('connection', async (ws) => {
  const firebaseUsers = await getUsersFromFirebase();
  // Bağlı olmayan kullanıcıları filtrele
  const availableUserIDs = firebaseUsers.filter(userID => !connectedUserIDs.has(userID)); 

  if (availableUserIDs.length === 0) {
    ws.send(JSON.stringify({ type: "error", message: "Mevcut kullanıcı yok" }));
    ws.close();
    return;
  }

  const randomIndex = Math.floor(Math.random() * availableUserIDs.length);
  const userID = availableUserIDs[randomIndex];

  users[userID] = ws;
  // Kullanıcı numarasını set'e ekle
  connectedUserIDs.add(userID); 
  ws.send(JSON.stringify({ type: "register", userID }));
  broadcastUserList();

  ws.on('message', (message) => { // mesaj dinleniyor
    const data = JSON.parse(message);
    if (data.target && users[data.target]) { // mesaj hedefe iletiliyor.
      users[data.target].send(JSON.stringify(data));
    }
  });

  ws.on('close', () => {
    if (users[userID]) {
      delete users[userID];
      // Kullanıcı numarasını set'ten çıkar
      connectedUserIDs.delete(userID); 
      broadcastUserList();
    }
  });

  ws.on('error', (error) => {
    console.error(`Kullanıcı için WebSocket hatası ${userID}:, error`);
  });
});

// HTTP sunucusunu başlatır.
httpsServer.listen(9090, () => {
  console.log(`Sunucu şu anda: https://< Your ip >:9090 çalışıyor`);
});


// HTTP bağlantısını bir websocket bağlantısına yükseltir.
httpsServer.on('upgrade', (request, socket, head) => {
  wss.handleUpgrade(request, socket, head, (ws) => {
    wss.emit('connection', ws, request);
  });
});
// handleUpgrade: Bağlantıyı alır ve WebSocket sunucusuna bağlar.

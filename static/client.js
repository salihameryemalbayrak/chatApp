//İstemci tarafında çalışan, WebSocket üzerinden kullanıcıların sesli arama yapmasını sağlayan kodlardır.

// IPv4 adresi, her seferinde güncel adres ile değiştirilmeli
const socket = new WebSocket("wss://192.168.247.1:9090"); 

//HTML'deki belirtilen öğelere erişimi sağlar.
const userList = document.getElementById("userList");
const startCallButton = document.getElementById("startCall");
const endCallButton = document.getElementById("endCall");
const statusDiv = document.getElementById("status");
const localAudio = document.getElementById("localAudio");
const remoteAudio = document.getElementById("remoteAudio");
const userIdInput = document.getElementById("userIdInput");
const myID = document.getElementById("myID");

// Gelen çağrı ekranı
const incomingCallDiv = document.createElement("div");
incomingCallDiv.id = "incomingCall";
incomingCallDiv.style.display = "none"; // varsayılan olarak gizledim.
incomingCallDiv.innerHTML = `
  <p id="incomingCallMessage"></p>
  <button id="acceptCall">Accept</button>
  <button id="rejectCall">Reject</button>
`;
document.body.appendChild(incomingCallDiv);

const acceptCallButton = document.getElementById("acceptCall");
const rejectCallButton = document.getElementById("rejectCall");
const incomingCallMessage = document.getElementById("incomingCallMessage");

let localStream;
let peerConnection;
// bu servere bağlanınca bizim için tanımlanan numara
let currentUserID;
// bu arama yapmak için seçeceğimiz kullanıcını numarası
let selectedUserID;

//ICE Sunucuları: WebRTC bağlantısını kurmak için kullanılan STUN Suncusudur.
// birden fazla url eklenebilir buraya
const configuration = {
  iceServers: [{ urls: "stun:stun.l.google.com:19302" }],
};

// Arama Kabul Etme ve ya Reddetme
// handleOffer, bir çağrı geldiğinde çalışır.
async function handleOffer(offer, from) {
  selectedUserID = from;

  // Gelen arama ekranını görünür yapma
  incomingCallDiv.style.display = "block";

  // Aramanın kimden geldiğini içeren mesaj
  incomingCallMessage.textContent = `${from}'dan gelen çağrı.`;
  
  // ----- Kabul et butonu tıklandığında -----
  acceptCallButton.onclick = async () => {
    // Gelen arama ekranını kapat.
    incomingCallDiv.style.display = "none";

    // WebRTC bağlantısı için bir RTCPeerConnection nesnesi oluşturulur.
    createPeerConnection();
    // Gelen offer'ın bilgisini peerConnection'a uzaktan oturum tanımı
    await peerConnection.setRemoteDescription(new RTCSessionDescription(offer)); 
    //RTCSessionDescription: WebRTC'de oturum bilgilerini içeren bir nesne.

    // Offer'a karşılık verilen cevap, yani Kabul Etme olayı.
    const answer = await peerConnection.createAnswer();
    // Cevabı peerConncection'a uygular
    await peerConnection.setLocalDescription(answer);

    socket.send(
      JSON.stringify({ // javascript'i JSON formatına dönüştürür.
        type: "answer", // answer, websocket üzerinden karşı tarafa gönderilir.
        // Gönderilen bilgiler
        answer, // aramanın cevabı
        target: from, //cevabın hedefi, yani arayan
        from: currentUserID, // cevabı veren kişinin kullanıcı kimliği
      })
    );
    updateStatus(`${from} ile görüşme yapılıyor.`); 
    startCallButton.classList.add("hidden"); //arama butonunu gizleme
    endCallButton.classList.remove("hidden"); //bitirme butonunu aktif etme
  };

  // ----- Reddet butonuna tıklabdığında -----
  rejectCallButton.onclick = () => {
    // Gelen arama ekranını kapat.
    incomingCallDiv.style.display = "none";


    //JSON.stringify, JavaScript nesnelerini JSON formatına çevirerek WebSocket mesajlarını 
    //anlaşılır, taşınabilir ve standart bir şekilde karşı tarafa iletmemizi sağlar.
    socket.send(
      JSON.stringify({
        type: "rejectCall",
        target: from,
        from: currentUserID,
      })
    );
    updateStatus(`${from}'dan gelen arama reddedildi.`); 
  };
}

// bildirimler
function updateStatus(message) {
  statusDiv.textContent = `Durum: ${message}`;
}

// kullanıcı hariç diğer kullanıcılarının numarasının gösterildiği liste.
function updateUserList(users) {
  users
    .filter((user) => user !== currentUserID)
    .forEach((user) => {
      const div = document.createElement("div");
      div.value = user;
      div.textContent = user;
      userList.appendChild(div);
    });
}

// Kullanıcının yerel mikrofonuna erişimi sağlar.
async function getLocalStream() {
  try {
    //mikrofona erişim talebi
    localStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    localAudio.srcObject = localStream;
    updateStatus("Arama yapmaya hazır");
  } catch (error) {
    console.error("Medya aygıtlarına erişim hatası:", error);
    updateStatus("Hata: Mikrofon kullanılamıyor.");
  }
}

// --- İKİ CİHAZ VE İKİ SEKME ARASINDA BAĞLANTI ---
// Webrtc bağlantısını kurar ve gerekli olay dişleyicileri ayarlar.
function createPeerConnection() {
  peerConnection = new RTCPeerConnection(configuration); //bağlantı kurma

  localStream
    .getTracks() //tüm medya parçaları alınır.
    .forEach((track) => peerConnection.addTrack(track, localStream));

  // event handlers: olay işleyiciler
  // ontrack ile karşı tarafın gönderdiği medya akışını remoteAudio'ya bağlar.
  peerConnection.ontrack = (event) => {
    remoteAudio.srcObject = event.streams[0];
  };

  // onicecandidate, ice adaylarını yakalar ve bir websocket mesajı olarak karşı tarafa iletir.
  peerConnection.onicecandidate = (event) => {
    if (event.candidate) {
      socket.send(
        JSON.stringify({
          type: "ice-candidate",
          candidate: event.candidate,
          target: selectedUserID,
        })
      );
    }
  };
}

// iki cihaz arasında bağlantı kurmak ve yönetmek için bir signal mekanizması
socket.onmessage = async (event) => {
  const message = JSON.parse(event.data);

  // bağlandım ve numaramın tanımlanmasını bekliyorum
  if (message.type === "register") {
    currentUserID = message.userID;
    myID.innerText = currentUserID;
    updateStatus(`${currentUserID} olarak bağlandı`);
  } else if (message.type === "user-list") {
    updateUserList(message.users);
  } else if (message.type === "offer") {
    await handleOffer(message.offer, message.from);
  } else if (message.type === "rejectCall") {
    await handleReject(message.from);
  } else if (message.type === "endCall") {
    await handleEndCall(message.from);
  } else if (message.type === "answer") {
    await handleAnswer(message.answer);
  } else if (message.type === "ice-candidate") {
    await handleIceCandidate(message.candidate);
  }
};

startCallButton.addEventListener("click", async () => {
  if (!userIdInput.value) {
    alert("Lütfen arama yapmak için bir kullanıcı seçin.");
    return;
  }
  // Hedef kullanıcının seçilip seçilmediğini kontrol etme

  // Hedef kullanıcı numarasını ayarlama
  selectedUserID = userIdInput.value;

  // yerel medya akışı kontrolü
  if (!localStream) {
    await getLocalStream();
  }

  //RTCPeerConnection nesnesi oluşturma
  createPeerConnection();
  const offer = await peerConnection.createOffer(); // teklif oluşturma
  await peerConnection.setLocalDescription(offer); // teklifi yerel nesneye tanımla

  socket.send(
    JSON.stringify({
      type: "offer",
      offer,
      target: selectedUserID,
      from: currentUserID,
    })
  );
  updateStatus(`${selectedUserID} aranıyor...`);
  startCallButton.classList.add("hidden");
  endCallButton.classList.remove("hidden");
});



async function handleAnswer(answer) {
  await peerConnection.setRemoteDescription(new RTCSessionDescription(answer));
  updateStatus(`${selectedUserID} ile çağrı bağlantısı kuruldu.`);
}

async function handleReject(from) {
  alert("Call rejected");
  updateStatus("Çağrı reddedildi:", from);

  startCallButton.classList.remove("hidden");
  endCallButton.classList.add("hidden");
}
async function handleEndCall(from) {
  alert("Call ended");
  updateStatus("Çağrı sona erdi:", from);

  startCallButton.classList.remove("hidden");
  endCallButton.classList.add("hidden");
}

async function handleIceCandidate(candidate) {
  if (peerConnection) {
    await peerConnection.addIceCandidate(new RTCIceCandidate(candidate));
  }
}

endCallButton.addEventListener("click", () => {
  if (peerConnection) {
    peerConnection.close();
    peerConnection = null;
  }

  socket.send(
    JSON.stringify({
      type: "endCall",
      target: selectedUserID,
      from: currentUserID,
    })
  );

  selectedUserID = null;
  updateStatus("Çağrı sona erdi");
  startCallButton.classList.remove("hidden");
  endCallButton.classList.add("hidden");
});

(async () => {
  await getLocalStream();
})();

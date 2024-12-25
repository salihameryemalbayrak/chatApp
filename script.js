const socket = io();

function logoutUser() {
socket.emit("logout"); // Socket üzerinden logout isteği gönder
//window.location.href = "{{ url_for('logout') }}"; // Çıkış işlemi için Flask yönlendirmesi
}

// Sunucuya bağlanma
socket.on("connect", () => {
    console.log("Sunucuya bağlandı.");
    socket.emit("users");
});


let activeUsersList = [];

socket.on("users", function(users) {
    const userList = document.getElementById("users-list");
    userList.innerHTML = ''; 

    for (const [userId, user] of Object.entries(users)) {
        if (user.username === "{{ session['kullaniciAdi'] }}") continue; // Oturum açan kullanıcıyı hariç tut veritabanındaki kullanıcıların hepsini tek tek gez

        const li = document.createElement("li");
        li.id = "user-" + userId;

        const a = document.createElement("a");
        a.href = `/private_chat/${userId}`;
        a.textContent = user.username;

        
        if (activeUsersList.includes(user.username)) {
            const dot = document.createElement("span");
            dot.classList.add("status-dot");
            a.appendChild(dot);
        }

        li.appendChild(a);
        userList.appendChild(li);
    }
});


socket.on("active_users", (activeUsers) => {
    activeUsersList = Object.values(activeUsers); 
    
    $("#users-list li").each(function() {
        const userId = $(this).attr("id").replace("user-", "");
        const username = $(this).find("a").text().trim(); 

        if (activeUsersList.includes(username)) { 
            if (!$(this).find(".status-dot").length) {
                const dot = document.createElement("span");
                dot.classList.add("status-dot");
                $(this).find("a").append(dot);
            }
        } else {
           
            $(this).find(".status-dot").hide();
        }
    });
});

socket.on("message_status_update", (data) => {
    // Gelen mesaj durumunu bulup güncelle
    const messageElements = document.querySelectorAll(".message");
    messageElements.forEach((messageElement) => {
        const timestamp = messageElement.querySelector(".timestamp").textContent;
        if (timestamp.includes(data.timestamp)) {
            const statusElement = messageElement.querySelector(".status");
            statusElement.textContent = data.status;
        }
    });
});

function sendBroadcastMessage() {
    const message = document.getElementById("broadcast-message").value;
    if (message) {
        socket.emit("broadcast_message", { message: message });
        document.getElementById("broadcast-message").value = '';
    }
}
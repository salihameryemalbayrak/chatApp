from flask import Flask, flash, jsonify , render_template,redirect, request, session, url_for
import socketio
from Forms import *
import time
from firebase_config22 import fire, dbase
import firebase_config22
from flask import Flask, render_template, request, session, redirect, url_for
from flask_socketio import join_room, leave_room, send, SocketIO, emit
from datetime import datetime
import random
import firebase_admin
from firebase_admin import credentials, db

app = Flask (__name__)
app.config["SECRET_KEY"] = '5a46fc92d36e604f423286c04875437f' 
dogrulama = fire.auth()
socketio = SocketIO(app)

rooms = {} 
active_users = {} 
room_active_users = {} 


def check_session_timeout():
    if 'last_activity' not in session:
        return redirect(url_for('login'))
    
    current_time = time.time()

    time_since_last_activity = current_time - session['last_activity']
    if time_since_last_activity > 300: 
        session.clear()  

        return redirect(url_for('login'))

    session['last_activity'] = current_time

@app.route("/arama", methods=["GET", "POST"])
def arama():
    if  not 'telefonNo' in session:
        print("cıkarıldı")
        return redirect("/Login")
    
    target = '' 
    
    if 'target_userid' in session :
        target = session['target_userid']
    
    benim_id = session['telefonNo']
    return render_template("index.html", arayan = benim_id , aranan = target )

@app.route("/", methods=["GET", "POST"])
@app.route("/KayitOl", methods=["GET", "POST"])
def kayitOl():
    form = YeniKayitFormu()

    if form.validate_on_submit():
        email = form.Eposta.data
        sifre = form.sifre.data
        telefon = form.telefonNo.data
        kullaniciAdi = form.kullaniciAdi.data
        
        for dosya in firebase_config22.tum_kullanicilar:
            us =  dosya.to_dict()
            if telefon == us["telefonNo"] :
                flash("Bu telefon no zaten kullanımda."," error")
                return render_template("KayitOl.html", baslik="Kayıt Ol", f=form)
            if email == us["email"] :
                flash("Bu e-posta adresi zaten kullanımda. Lütfen başka bir e-posta girin"," error")
                return render_template("KayitOl.html", baslik="Kayıt Ol", f=form)

        try:
            uye = dogrulama.create_user_with_email_and_password(email, sifre)
            uye_id = uye['localId'] 
            
            user_data = {
                "telefonNo": telefon,
                "kullaniciAdi": kullaniciAdi,
                "email": email 
            }

            dbase.collection("users").document(uye_id).set(user_data) 
            flash("Kayıt başarılı! ", "success")
            session['last_activity'] = time.time()
            session["telefonNo"] = telefon
            session["kullaniciAdi"] = kullaniciAdi
            return redirect(url_for('home'))
        
        except Exception as e:
            flash("Bir hata oluştu. Lütfen daha sonra tekrar deneyin.", "error")
    
    return render_template("KayitOl.html", baslik="Kayıt Ol", f=form)

@app.route("/Login",methods =["GET","POST"] )
def login():
    form2 = LoginForm()

    if form2.validate_on_submit():              
        email = form2.Eposta.data
        sifre = form2.sifre.data                               
        try:
            user = dogrulama.sign_in_with_email_and_password(email, sifre)
            if user:
                print(f"Giriş başarılı. Kullanıcı ID: {user['localId']}")
                session['user_id'] = user['localId']
                session['email'] = email
                session['telefonNo'] = dbase.collection("users").document(user['localId']).get().to_dict().get('telefonNo')     
                session['kullaniciAdi'] = dbase.collection("users").document(user['localId']).get().to_dict().get('kullaniciAdi')
                session['last_activity'] = time.time()
                flash("Giriş başarılı.!", "success")
                return redirect(url_for('home'))  
            else:
                flash("Giriş bilgileri yanlış. Lütfen tekrar deneyin.", "error")
        except Exception as e:
            flash("Giriş yaparken bir hata oluştu: ", "error")

    return render_template("GirisYap.html", baslik="Login", f=form2)
@socketio.on("update_message_status")
def handle_status_update(data):
    user_id = data.get("user_id")
    if user_id:
        ref = db.reference('rooms')
        rooms = ref.get()
        if rooms:
            for room_id in rooms.items():
                ref2 = db.reference(f'rooms/{room_id}/message_data')
                messages_snapshot = ref2.get()
                if messages_snapshot:
                    for key, message in messages_snapshot.items():
                        if message["receiver"] == user_id:
                            ref2.child(key).update({"status": "iletildi"})
                            socketio.emit("message_status_update", {"timestamp": message["timestamp"], "status": "iletildi"}, to=room_id)
             
@app.route("/sifremiUnuttum", methods=["GET", "POST"])
def sifremiunuttum():
    form3 = SifreSifirlama()
    if form3.validate_on_submit():
        email = form3.eposta.data
        try:
            dogrulama.send_password_reset_email(email)
            flash("E-posta adresinize şifre sıfırlama bağlantısı gönderildi.", "success")
            return redirect("/Login")
        except Exception as e:
            flash("Bir hata oluştu: " + str(e), "error")
    return render_template("sifremiUnuttum.html", baslik="Forgot password", f=form3)

@app.route("/home",methods=["GET","POST"])
def home():
    kullanici_adi = session.get("kullaniciAdi", "Bilinmeyen Kullanıcı")
    telefon_no = session.get("telefonNo", "Telefon Numarası Yok")
    print(f"Kullanıcı Adı: {kullanici_adi}, Telefon No: {telefon_no}")
    user_ip = request.remote_addr
    print("user ip is:--------------------")
    print(user_ip)
    user_id = telefon_no
    if user_id in room_active_users:
        room_active_users[rooms].remove(user_id)
        socketio.emit("room_active_users", room_active_users)
    
    try:
        result = check_session_timeout()
        if result:  
            return result
        mesajdurumuiletildi(telefon_no) 
        kullaniciAdlari = [
        {
            "ad": doc.to_dict().get("kullaniciAdi", "Bilinmeyen Kullanıcı"),
            "telefonNo": doc.to_dict().get("telefonNo", "Telefon Yok"),
        }
        for doc in firebase_config22.tum_kullanicilar
        if doc.to_dict().get("telefonNo") != telefon_no 
            ]
        arama = request.form.get('sea')
        
        if arama:
            kullaniciAdlari = [k for k in kullaniciAdlari if arama.lower() in k['ad'].lower() or arama in k['telefonNo']]

        else : 
            arama =""
        
        return render_template("home.html",  users = kullaniciAdlari, ar =arama)
    except Exception as e:
        print(e)
        flash("Bir hata oluştu. Lütfen daha sonra tekrar deneyin.", "error")
        return redirect(url_for("kayitOl"))
    


def listen_for_message_updates(room_id):
    ref= db.reference(f'rooms/{room_id}')
    ref.child('message').listen(private_chat()) 

@app.route("/private_chat/<target_user_id>/<target_username>")
def private_chat(target_user_id, target_username):
    room_id = f"{min(session['telefonNo'], target_user_id)}-{max(session['telefonNo'], target_user_id)}"
    session["room_id"] = room_id
    oturum_yonetimi = check_session_timeout()
    if oturum_yonetimi :
        flash("oturumunuz zaman aşımına uğradı")
        return oturum_yonetimi
    session['target_userid'] = target_user_id
    session['target_username'] = target_username
    ref = db.reference(f'rooms/{room_id}/message_data')
    data = ref.get()

    n = []
    if data:
        for  key,value in data.items():
            n.append(value)

    messages = n
    return render_template("private_chat.html", room_id=room_id, messages=messages, target_user=target_username,target_user_id=target_user_id)

@socketio.on("join_room")
def join(data):
    join_room(data["room_id"])
    
@socketio.on("leave_room")
def handle_leave_room(data):
    room_id = data.get("room_id")
    user_id = session.get("telefonNo")
    
    if room_id and user_id:
        leave_room(room_id)
        if room_id in room_active_users and user_id in room_active_users[room_id]:
            room_active_users[room_id].remove(user_id)
            socketio.emit("room_active_users", room_active_users)
            
    
@socketio.on("connect")
def handle_connect():
    user_id = session.get("telefonNo")
    username = session.get("kullaniciAdi")
    if user_id and username:
        active_users[user_id] = username ################ Salihaya telefonNo yerine neden kullanıcı adını yazdığını sor 
        # mesajdurumuiletildi(user_id)   ################ fonksiyonun buradan mı yoksa home'den çağrılacağına karar vermeden salihaya sor  



def mesajdurumuiletildi(user_id) :
    ref = db.reference('rooms')
    rooms = ref.get()
    for room in rooms :
        if user_id in room :
            referance = db.reference(f'rooms/{room}/message_data')
            messages_snapshot = referance.get()

            for key, message in messages_snapshot.items():
                if message["receiver"] == user_id and message["status"] =="gönderildi":
                    referance.child(key).update({"status": "iletildi"})
                    socketio.emit("message_status_update", {"timestamp": message["timestamp"], "status": "iletildi"}, to=room)
    print("tekrar baglandi")

@socketio.on("disconnect")
def handle_disconnect():
    user_id = session.get("telefonNo")
    room_id = session.get("room_id")

    if user_id in active_users:
        room_active_users.pop(user_id)
        room_active_users[room_id].remove(user_id)
        socketio.emit("room_active_users", room_active_users)

print("Bağlantı kesildi")  

@socketio.on("message")
def handle_message(data):
    room_id = session.get("room_id")
    if not room_id:
        return

    sender_user_id = session["telefonNo"]
    user_ids = room_id.split("-")
    target_user_id = user_ids[1] if user_ids[0] == sender_user_id else user_ids[0]

    message_data = {
        "sender_name": session["kullaniciAdi"],
        "sender": sender_user_id,
        "receiver": target_user_id,
        "message": data["message"],
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "gönderildi"
    }

    if target_user_id in active_users:
        message_data["status"] = "İletildi"
        
    if target_user_id in room_active_users[room_id]:
        message_data["status"] = "Görüldü"

    ref = db.reference(f'rooms/{room_id}/message_data')
    ref.push(message_data)

    send(message_data, to=room_id)
    socketio.emit("message_status_update", {"timestamp": message_data["timestamp"], "status": message_data["status"]}, to=room_id)

@socketio.on("join")
def on_join():
    room_id = session.get("room_id")
    user_id = session.get("telefonNo")

    if not room_id:
        return
    join_room(room_id)

    if room_id not in room_active_users:
        room_active_users[room_id] = []
    if user_id not in room_active_users[room_id]:
        room_active_users[room_id].append(user_id)

    ref = db.reference(f'rooms/{room_id}/message_data')
    messages_snapshot = ref.get()
    if messages_snapshot:
        for key, message in messages_snapshot.items():
            if message["receiver"] == user_id:
                ref.child(key).update({"status": "Görüldü"})
                socketio.emit("message_status_update", {"timestamp": message["timestamp"], "status": "Görüldü"}, to=room_id)

@socketio.on("broadcast_message")
def handle_broadcast_message(data):
    # Gönderen kullanıcının oturum bilgilerini kontrol et
    if "kullaniciAdi" not in session or not session["kullaniciAdi"]:
        print("Hata: Gönderen kullanıcının oturum bilgileri eksik.")
        return  # Eğer kullanıcı oturumu geçerli değilse işlemi sonlandır

    sender_user_id = session["telefonNo"]  # Gönderenin telefon numarası
    sender_name = session["kullaniciAdi"]  # Gönderenin kullanıcı adı

    # Mesaj verisi
    message_text = data.get("message", "")
    if not message_text.strip():
        print("Hata: Mesaj metni boş.")
        return

    for target_user_id in active_users:  # Aktif kullanıcılar üzerinde döngü yap
        if target_user_id == sender_user_id:
            continue  # Kendi kendine mesaj göndermeyi atla

        # Oda ID'sini belirle
        room_id = f"{min(sender_user_id, target_user_id)}-{max(sender_user_id, target_user_id)}"

        # Mesaj verisi
        message_data = {
            "sender_name": sender_name,
            "sender": sender_user_id,
            "receiver": target_user_id,
            "message": message_text,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "status": "gönderildi"  # İlk durum
        }

        # Durumu "İletildi" veya "Görüldü" olarak güncelle
        if target_user_id in active_users:
            message_data["status"] = "İletildi"
        if room_id in room_active_users and target_user_id in room_active_users[room_id]:
            message_data["status"] = "Görüldü"

        # Mesajı veritabanına ekle
        ref = db.reference(f'rooms/{room_id}/message_data')
        ref.push(message_data)

        # Odaya mesajı yayınla
        socketio.emit("message", message_data, room=room_id)

    print(f"Broadcast mesaj gönderildi: {message_text}")


@socketio.on("message_status_update")
def message_status_update(data):
    room_id = data['room_id']
    timestamp = data['timestamp']
    ref = db.reference(f'rooms/{room_id}/message_data')
    messages = ref.get()

    for message_id, message in messages.items():
        if message["timestamp"] == timestamp:
            new_status = data["status"]
            ref.child(message_id).update({"status": new_status})
            socketio.emit("message_status_update", {"timestamp": timestamp, "status": new_status}, to=room_id)
            break

@app.route("/logout",methods=["POST"])
def logout():
    user_id = session.get("telefonNo")
    if user_id:
        session.pop("telefonNo", None)
        session.pop("kullaniciAdi", None)
        active_users.pop(user_id, None)
        socketio.emit("active_users", active_users)
        print("çıkış basarılı")
    return redirect(url_for("login"))        
        
"""if __name__ == "__main__": 
    app.run(port=5000,debug=True,ssl_context=('server.cert','server.key'))"""
if __name__ == "__main__": 
    socketio.run(app, host='0.0.0.0', port=5000, debug=True,ssl_context=('server.cert','server.key'))

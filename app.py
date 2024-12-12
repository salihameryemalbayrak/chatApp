from flask import Flask, flash , render_template,redirect, request, session, url_for
import socketio
from Forms import *
import time
from firebase_config22 import fire,db
import firebase_config22
from flask import Flask, render_template, request, session, redirect, url_for
from flask_socketio import join_room, leave_room, send, SocketIO, emit
from datetime import datetime
import random

app = Flask (__name__)
app.config["SECRET_KEY"] = '5a46fc92d36e604f423286c04875437f' 
dogrulama = fire.auth()
socketio = SocketIO(app)

users = {}  #veritabanında olmalı
rooms = {}  #veritabanında olmalı
active_users = {} 
room_active_users = {} 


def check_session_timeout():
    
    if 'last_activity' not in session:
        return redirect(url_for('login'))

    # Şu anki zaman
    current_time = time.time()

    # Son aktivite zamanı ile şu anki zaman farkı
    time_since_last_activity = current_time - session['last_activity']
    if time_since_last_activity > 300:  # 300 saniye = 5 dakika
        session.clear()  
        return redirect(url_for('login'))

    session['last_activity'] = current_time


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
            # dogrulama.send_email_verification(uye['idToken'])
            uye_id = uye['localId'] 
            
            user_data = {
                "telefonNo": telefon,
                "kullaniciAdi": kullaniciAdi,
                "email": email 
            }

            db.collection("users").document(uye_id).set(user_data) 
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

    if form2.validate_on_submit():                   #!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        email = form2.Eposta.data
        sifre = form2.sifre.data                                #kullanici adi ve tel noyu almaaa
      #  telefonNo = db.collection("users").document(user['localId']).get().to_dict().get('telefonNo')       #sessiona eklemem gerek
       # kullaniciAdi = db.collection("users").document(user['localId']).get().to_dict().get('kullaniciAdi')
        try:
            user = dogrulama.sign_in_with_email_and_password(email, sifre)
            if user:
                print(f"Giriş başarılı. Kullanıcı ID: {user['localId']}") # terminalde yazdırılacak
                session['user_id'] = user['localId']
                session['email'] = email
                session['telefonNo'] = db.collection("users").document(user['localId']).get().to_dict().get('telefonNo')       #sessiona eklemem gerek
                session['kullaniciAdi'] = db.collection("users").document(user['localId']).get().to_dict().get('kullaniciAdi')
                session['last_activity'] = time.time()
                flash("Giriş başarılı.!", "success")
                return redirect(url_for('home'))  
            else:
                flash("Giriş bilgileri yanlış. Lütfen tekrar deneyin.", "error")
        except Exception as e:
            flash("Giriş yaparken bir hata oluştu: ", "error")

    return render_template("GirisYap.html", baslik="Login", f=form2)

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

    #user_id = request.args.get('user_id')
    #print(f"hello {user_id}")
   # telefonNo = session[telefonNo]
   # kullaniciAdi = session[kullaniciAdi]
    kullanici_adi = session.get("kullaniciAdi", "Bilinmeyen Kullanıcı")
    telefon_no = session.get("telefonNo", "Telefon Numarası Yok")
    print(f"Kullanıcı Adı: {kullanici_adi}, Telefon No: {telefon_no}")

    # if not user_id:
    #     flash("Geçersiz kullanıcı ID'si.", "error")
    #     return redirect(url_for("kayitOl"))
    
    try:
        
        kullaniciAdlari = [
            {
                "ad": doc.to_dict().get("kullaniciAdi", "Bilinmeyen Kullanıcı"),
                "telefonNo": doc.to_dict().get("telefonNo", "Telefon Yok"),
            }
            for doc in firebase_config22.tum_kullanicilar
        ]
        
        # Oturum kontrolü
        result = check_session_timeout()
        if result:  
            return result
        
        return render_template("home.html",  users = kullaniciAdlari )
    except Exception as e:
        flash("Bir hata oluştu. Lütfen daha sonra tekrar deneyin.", "error")
        return redirect(url_for("kayitOl"))
    
@app.route("/private_chat/<target_user_id>/<target_username>")
def private_chat(target_user_id, target_username):
    room_id = f"{min(session['telefonNo'], target_user_id)}-{max(session['telefonNo'], target_user_id)}"
    if room_id not in rooms:        #odayı veritabanına ekleme !!!!!!!!!!!!!!!!!!!!!!!!!!!!
        rooms[room_id] = []            

    session["room_id"] = room_id
    #target_username =users[target_user_id]["username"]          #!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! karşı taraf kullanıcının ismine ulaşmam lazım
    #target_username = db.collection("users").document(user['localId']).get().to_dict().get('kullaniciAdi')
    messages = rooms[room_id]
    return render_template("private_chat.html", room_id=room_id, messages=messages, target_user=target_username)
    
@socketio.on("users")
def handle_request_users():
       
       socketio.emit("users", users)
    
    
@socketio.on("connect")
def handle_connect():
    user_id = session.get("telefonNo")                          ##veritabanından alınacak
    username = session.get("kullaniciAdi")
    if user_id and username:
        active_users[user_id] = username
        socketio.emit("active_users", active_users)
       
        for room_id, messages in rooms.items():
            for message in messages:
                if message["receiver"] == user_id and message["status"] != "iletildi":      ##mesaj durumu güncellemesi alıcısına göre mesaj durumunu değiştiriyo
                    message["status"] = "İletildi"
                    socketio.emit("message_status_update", message, room=room_id)    
    print("tekrar baglandi")
@socketio.on("disconnect")
def handle_disconnect():
    user_id = session.get("telefonNo")      ##veritabanından alinacak
    room_id = session.get("room_id")

   ##eklendiğinde üstteki geri tuşu ile çıkış yapılıyor fakat o zaman da private chat sayfasından geri tuşuna basıldığında da çıktığı için mesaj atamıyor sayfa yeniden yüklenene kadar
    """
    if user_id in active_users:
        active_users.pop(user_id)
        socketio.emit("active_users", active_users)
    """
    #böyle olunca da mesaj atan kişi geri çıktığı zaman kısa bir süre toplu mesaj atamıyor

    if room_id and user_id in room_active_users.get(room_id, []):
        room_active_users[room_id].remove(user_id)   
    print("Bağlantı kesildi")  

@socketio.on("message")
def handle_message(data):
    print("mesaj burdan gonderilmeye calisiliyor")
    room_id = session.get("room_id")        ##emin değilim nerden alınması gerek
    if not room_id:
        return
    
    # Oda ID'sinden alıcıyı belirle
    user_ids = room_id.split("-")

    # Gönderen kimliği, session içindeki kullanıcı kimliği
    sender_user_id = session["telefonNo"]

    # Alıcıyı belirle: Gönderenin dışındaki kullanıcı
    if user_ids[0] == sender_user_id:
        target_user_id = user_ids[1]
    else:
        target_user_id = user_ids[0]

    
    message_data = {
        "name": session["kullaniciAdi"],
        "receiver": target_user_id,  
        "message": data["message"],                                          
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "gönderildi"
    }

     
    if target_user_id in active_users:                                           
        message_data["status"] = "İletildi"         #veritabanı guncellenmeli
    
    
    if target_user_id in room_active_users.get(room_id, []):               
        message_data["status"] = "Görüldü"                         #veritabanı guncellenmeli

    
    rooms[room_id].append(message_data)     #mesajların veritabanınna eklenmesi

   
    send(message_data, to=room_id)
    emit("message_status_update", message_data, to=room_id)


@socketio.on("join")
def on_join():
    room_id = session.get("room_id")          #emin değilim nerden alınmalı
    user_id = session.get("kullaniciAdi")
    if not room_id:
        return
    join_room(room_id)

    
    if room_id not in room_active_users:
        room_active_users[room_id] = []
    room_active_users[room_id].append(user_id)

    
    for message in rooms[room_id]:
        if message["receiver"] == user_id and message["status"] != "Görüldü":
                    message["status"] = "Görüldü"                                            ##mesaj durumu güncellenecek
                    socketio.emit("message_status_update", message, room=room_id)


@socketio.on("broadcast_message")
def handle_broadcast_message(data):
    message_data = {
        "name": session["kullaniciAdi"],
        "receiver":active_users,  
        "message": data["message"],                                           ##mesaj burada veritabanına alınacak gönderici ve alıcı bilgisiyle beraber
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": ""
    }
    for user_id in active_users:
        room_id = f"{min(session['telefonNo'], user_id)}-{max(session['telefonNo'], user_id)}"
        rooms.setdefault(room_id, []).append(message_data)               ##rooms veritabanından geleck
        socketio.emit("message", message_data, room=room_id)

@app.route("/logout")                   #çıkış yapınca çalıştırılmalı
def logout():
    user_id = session.get("telefonNo")
    if user_id:
        session.pop("telefonNo", None)
        session.pop("kullaniciAdi", None)
        active_users.pop(user_id, None)
        socketio.emit("active_users", active_users)
    return redirect(url_for("home"))        
  
        
if __name__ == "__main__": 
    app.run(debug=True)

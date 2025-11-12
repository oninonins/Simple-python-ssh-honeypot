import socket
import threading
import datetime

# --- Konfigurasi ---
HOST = '0.0.0.0'  # listen di semua interface. '0.0.0.0' berarti bisa diakses dari IP manapun, 
PORT = 2222       # Port non-standar. Hindari port 22 asli agar tidak butuh hak akses root.
LOG_FILE = 'honeypot.log' # Nama file untuk menyimpan semua log aktivitas.

# --- Fungsi Logging ---
def log_data(ip, port, data_str):
    """Mencatat aktivitas ke file log dan juga menampilkannya di konsol."""
    
    # Format timestamp agar mudah dibaca
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] Koneksi dari {ip}:{port} - Data: {data_str}\n"
    
    print(log_entry, end='') # Tampilkan di konsol secara real-time
    
    # Gunakan 'with open' agar file otomatis ditutup (safe-handling).
    # Mode 'a' (append) berarti 'tambahkan di akhir file', jangan timpa (overwrite).
    try:
        with open(LOG_FILE, 'a') as f:
            f.write(log_entry)
    except Exception as e:
        print(f"(!) Gagal menulis ke file log: {e}")

# --- Fungsi untuk Menangani Tiap Koneksi ---
def handle_client(client_socket, client_address):
    """
    Fungsi ini dijalankan di thread baru setiap kali ada koneksi masuk.
    Ini adalah inti dari logika 'pura-pura' honeypot kita.
    """
    ip, port = client_address
    print(f"[+] Koneksi baru diterima dari {ip}:{port}")

    # 1. Kirim Banner Palsu
    #    Kita langsung berpura-pura menjadi server OpenSSH agar penyerang 
    #    mengira ini adalah target sungguhan.
    try:
        banner = b"SSH-2.0-OpenSSH_8.2p1\r\n" # \r\n adalah standar 'Enter' di protokol jaringan
        client_socket.send(banner)
    except Exception as e:
        print(f"[!] Error kirim banner ke {ip}:{port}: {e}")
        client_socket.close()
        return # Hentikan fungsi jika gagal kirim banner

    # 2. Terima Data (Username/Password)
    #    Setelah mengirim banner, kita tunggu penyerang mengirimkan data.
    try:
        # Kita baca data yang masuk, maksimal 1024 bytes
        data = client_socket.recv(1024) 
        
        if data:
            # Decode data dari 'bytes' (yang diterima socket) ke 'string' (yang bisa dibaca).
            # 'errors='ignore'' untuk menangani jika ada karakter aneh/non-UTF-8.
            data_str = data.decode('utf-8', errors='ignore').strip()
            
            # Catat datanya! Ini adalah bagian terpenting dari honeypot.
            log_data(ip, port, data_str)
            
            # 3. Kirim Pesan Error Palsu
            #    Setelah dapat datanya, kita kirim pesan error palsu lalu putus koneksi.
            error_msg = b"Password authentication failed.\r\n"
            client_socket.send(error_msg)
            
            # --- TODO untuk Pengembangan ---
            # TODO: Daripada langsung kirim error, kita bisa 'bermain' lebih lama.
            #       Misalnya, pura-pura minta password lagi, atau pura-pura menerima perintah.
            # TODO: Coba parsing 'data_str' untuk memisahkan username dan password jika memungkinkan.

    except socket.timeout:
        # Jika klien terhubung tapi diam saja (tidak mengirim apa-apa)
        print(f"[-] Koneksi timeout dari {ip}:{port}")
    except Exception as e:
        print(f"[!] Error saat menangani klien {ip}:{port}: {e}")
    
    finally:
        # 4. Tutup Koneksi
        #    PENTING: Selalu tutup socket klien untuk membebaskan sumber daya.
        print(f"[-] Menutup koneksi dari {ip}:{port}")
        client_socket.close()

# --- Fungsi Utama Server ---
def start_server():
    """Mempersiapkan dan memulai server socket utama."""
    
    # AF_INET = menggunakan protokol IPv4
    # SOCK_STREAM = menggunakan protokol TCP (koneksi yang handal, bukan UDP)
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    # Opsi ini agar kita bisa langsung menjalankan ulang server setelah di-stop
    # (menghindari error "Address already in use").
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server.bind((HOST, PORT))
        server.listen(5) # Izinkan antrian hingga 5 koneksi sebelum menolak koneksi baru
        print(f"[*] Honeypot mendengarkan di {HOST}:{PORT}...")

        # Loop utama server (tidak pernah berhenti)
        while True:
            # server.accept() akan 'memblokir' (berhenti) di sini sampai ada koneksi baru.
            # Saat ada koneksi, ia mengembalikan socket klien dan alamatnya.
            client_socket, client_address = server.accept()
            
            # Buat thread baru untuk menangani klien ini.
            # Ini agar loop utama bisa langsung kembali ke 'server.accept()' 
            # untuk menunggu koneksi lain, tanpa harus menunggu klien pertama selesai.
            client_handler = threading.Thread(
                target=handle_client, 
                args=(client_socket, client_address)
            )
            client_handler.start()

    except KeyboardInterrupt:
        print("\n[!] Server dihentikan. (Ctrl+C)")
    except Exception as e:
        print(f"[!] Server error: {e}")
    finally:
        server.close()
        print("[*] Server socket ditutup.")

# --- Jalankan Server ---
# Ini adalah cara standar Python untuk menjalankan kode hanya jika file ini
# dieksekusi sebagai skrip utama (bukan di-import sebagai library oleh file lain).
if __name__ == "__main__":
    start_server()
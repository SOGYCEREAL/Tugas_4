import sys
import socket
import os
import uuid

# --- SESUAIKAN ALAMAT SERVER DI SINI ---
# Ganti dengan alamat IP dan port server Anda.
# Port harus sama dengan yang dijalankan oleh server
# (server_thread_pool_http.py atau server_process_pool_http.py)
SERVER_HOST = '172.16.16.101'
SERVER_PORT = 6930
# -----------------------------------------

def send_request(request_data):
    """
    Fungsi generik untuk mengirim request ke server dan menerima respons penuh.
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_address = (SERVER_HOST, SERVER_PORT)
        print(f"Connecting to {server_address}...")
        sock.connect(server_address)

        # Mengirim data request dalam bentuk bytes
        sock.sendall(request_data)

        # Menerima respons dari server
        # Baca header terlebih dahulu
        headers = b""
        while b"\r\n\r\n" not in headers:
            part = sock.recv(1)
            if not part:
                break
            headers += part
        
        headers_str = headers.decode('utf-8', errors='ignore')
        print("--- SERVER RESPONSE HEADERS ---")
        print(headers_str)

        # Cek Content-Length untuk tahu ukuran body
        content_length_line = next((line for line in headers_str.split('\r\n') if 'Content-Length:' in line), None)
        body = b""
        if content_length_line:
            content_length = int(content_length_line.split(' ')[1])
            while len(body) < content_length:
                part = sock.recv(content_length - len(body))
                if not part:
                    break
                body += part
        
        print("--- SERVER RESPONSE BODY ---")
        print(body.decode('utf-8', errors='ignore'))

    except Exception as e:
        print(f"Error: {e}")
    finally:
        sock.close()


def list_files(directory='/'):
    """
    Meminta daftar file dari direktori di server.
    """
    print(f"Requesting file list from directory: {directory}")
    request_str = f"GET {directory} HTTP/1.1\r\n"
    request_str += f"Host: {SERVER_HOST}:{SERVER_PORT}\r\n"
    request_str += "Connection: close\r\n"
    request_str += "\r\n"
    
    send_request(request_str.encode())


def upload_file(local_filepath):
    """
    Mengupload file ke server menggunakan POST multipart/form-data.
    """
    if not os.path.exists(local_filepath):
        print(f"Error: File '{local_filepath}' not found locally.")
        return

    filename = os.path.basename(local_filepath)
    
    # Baca konten file dalam mode binary
    with open(local_filepath, 'rb') as f:
        file_content = f.read()

    # Buat boundary yang unik
    boundary = f"----WebKitFormBoundary{uuid.uuid4().hex}"
    
    # Bangun body request
    body = []
    body.append(f'--{boundary}')
    body.append(f'Content-Disposition: form-data; name="file"; filename="{filename}"')
    body.append('Content-Type: application/octet-stream') # Tipe konten generik
    body.append('')
    body.append(file_content)
    body.append(f'--{boundary}--')
    body.append('')
    
    # Gabungkan body menjadi satu blok bytes dengan pemisah \r\n
    # Konten file sudah bytes, jadi kita encode string lainnya
    body_parts_bytes = [p.encode() if isinstance(p, str) else p for p in body]
    request_body = b'\r\n'.join(body_parts_bytes)

    # Bangun header request
    request_header = f"POST /upload HTTP/1.1\r\n"
    request_header += f"Host: {SERVER_HOST}:{SERVER_PORT}\r\n"
    request_header += f"Content-Type: multipart/form-data; boundary={boundary}\r\n"
    request_header += f"Content-Length: {len(request_body)}\r\n"
    request_header += "Connection: close\r\n"
    request_header += "\r\n"

    # Gabungkan header dan body menjadi satu request utuh
    full_request = request_header.encode() + request_body
    
    print(f"Uploading file '{filename}'...")
    send_request(full_request)


def delete_file(server_filepath):
    """
    Menghapus file di server.
    """
    print(f"Requesting to delete file: {server_filepath}")
    request_str = f"DELETE /{server_filepath} HTTP/1.1\r\n"
    request_str += f"Host: {SERVER_HOST}:{SERVER_PORT}\r\n"
    request_str += "Connection: close\r\n"
    request_str += "\r\n"

    send_request(request_str.encode())


def print_usage():
    print("Usage:")
    print("python client.py list [direktori_server]")
    print("python client.py upload [path_file_lokal]")
    print("python client.py delete [path_file_di_server]")
    print("\nExamples:")
    print("  python client.py list /")
    print("  python client.py upload mydocument.txt")
    print("  python client.py delete uploads/mydocument.txt")

if __name__ == '__main__':
    while True:
        print("\n--- File Management Client ---")
        print("1. List files")
        print("2. Upload file")
        print("3. Delete file")
        print("4. Exit")
        choice = input("Select an option (1-4): ").strip()

        if choice == '1':
            directory = input("Enter directory path on server (default '/'): ").strip()
            if directory == '':
                directory = '/'
            list_files(directory)

        elif choice == '2':
            local_path = input("Enter local file path to upload: ").strip()
            upload_file(local_path)

        elif choice == '3':
            server_path = input("Enter path of file on server to delete: ").strip()
            delete_file(server_path)

        elif choice == '4':
            print("Exiting client.")
            break

        else:
            print("Invalid option. Please choose 1, 2, 3, or 4.")
from socket import *
import socket
import time
import sys
import logging
# Import ThreadPoolExecutor, bukan ProcessPoolExecutor
from concurrent.futures import ThreadPoolExecutor
from http import HttpServer

httpserver = HttpServer()

# Fungsi ini sudah benar dan tidak perlu diubah.
# Bisa digunakan oleh ThreadPool dan ProcessPool.
def ProcessTheClient(connection, address):
    try:
        # 1. Baca header terlebih dahulu
        headers = b""
        while b"\r\n\r\n" not in headers:
            data = connection.recv(1)
            if not data:
                break
            headers += data
        
        # 2. Cari Content-Length dari header
        content_length = 0
        header_lines = headers.decode('utf-8', errors='ignore').split('\r\n')
        for line in header_lines:
            if line.lower().startswith('content-length:'):
                content_length = int(line.split(':')[1].strip())
                break
        
        # 3. Baca body (isi file) sesuai Content-Length
        body = b""
        while len(body) < content_length:
            data = connection.recv(content_length - len(body))
            if not data:
                break
            body += data

        # 4. Gabungkan kembali menjadi request HTTP utuh
        full_request = headers + body

        # 5. Proses request dan kirim respons
        hasil = httpserver.proses(full_request)
        connection.sendall(hasil)

    except Exception as e:
        print(f"Error processing client: {e}")
    finally:
        connection.close()
    return

def Server():
	the_clients = []
	my_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

	# Pastikan portnya sesuai, contoh 4200
	my_socket.bind(('0.0.0.0', 6930))
	my_socket.listen(1)

	# --- SATU-SATUNYA PERUBAHAN ADA DI BARIS INI ---
	with ThreadPoolExecutor(20) as executor:
		while True:
				connection, client_address = my_socket.accept()
				print(f"Connection from {client_address}")
				
				# Submit pekerjaan ke thread pool
				executor.submit(ProcessTheClient, connection, client_address)
				
				# Bagian di bawah ini opsional, hanya untuk melihat jumlah thread aktif
				# Jika Anda ingin, Anda bisa menghapusnya
				# the_clients.append(p)
				# jumlah = ['x' for i in the_clients if i.running()==True]
				# print(jumlah)

def main():
	Server()

if __name__=="__main__":
	main()
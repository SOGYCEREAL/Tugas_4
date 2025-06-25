from socket import *
import socket
import time
import sys
import logging
import multiprocessing
from concurrent.futures import ProcessPoolExecutor
from http import HttpServer

httpserver = HttpServer()

#untuk menggunakan processpoolexecutor, karena tidak mendukung subclassing pada process,
#maka class ProcessTheClient dirubah dulu menjadi function, tanpda memodifikasi behaviour didalamnya

def ProcessTheClient(connection, address):
    try:
        # 1. Baca header terlebih dahulu
        headers = b""
        while b"\r\n\r\n" not in headers:
            data = connection.recv(1)
            if not data:
                break
            headers += data
        
        # Pisahkan request line dan headers untuk debugging jika perlu
        # print("Headers received:\n", headers.decode())

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

	my_socket.bind(('0.0.0.0', 4200))
	my_socket.listen(1)

	with ProcessPoolExecutor(20) as executor:
		while True:
				connection, client_address = my_socket.accept()
				#logging.warning("connection from {}".format(client_address))
				p = executor.submit(ProcessTheClient, connection, client_address)
				the_clients.append(p)
				#menampilkan jumlah process yang sedang aktif
				jumlah = ['x' for i in the_clients if i.running()==True]
				print(jumlah)

def main():
	Server()

if __name__=="__main__":
	main()


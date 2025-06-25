import sys
import os
import os.path
import uuid
from glob import glob
from datetime import datetime
import re # Diperlukan untuk parsing multipart

class HttpServer:
    def __init__(self):
        self.sessions = {}
        self.types = {}
        self.types['.pdf'] = 'application/pdf'
        self.types['.jpg'] = 'image/jpeg'
        self.types['.txt'] = 'text/plain'
        self.types['.html'] = 'text/html'
        self.upload_dir = './uploads/' # Direktori untuk menyimpan file upload
        if not os.path.exists(self.upload_dir):
            os.makedirs(self.upload_dir)

    def response(self, kode=404, message='Not Found', messagebody=bytes(), headers={}):
        tanggal = datetime.now().strftime('%c')
        resp = []
        resp.append(f"HTTP/1.0 {kode} {message}\r\n")
        resp.append(f"Date: {tanggal}\r\n")
        resp.append("Connection: close\r\n")
        resp.append("Server: myserver/1.0\r\n")
        resp.append(f"Content-Length: {len(messagebody)}\r\n")
        for kk in headers:
            resp.append(f"{kk}:{headers[kk]}\r\n")
        resp.append("\r\n")

        response_headers = ''
        for i in resp:
            response_headers = f"{response_headers}{i}"
        
        if not isinstance(messagebody, bytes):
            messagebody = messagebody.encode()

        response = response_headers.encode() + messagebody
        return response

    def proses(self, data):
        requests = data.split(b"\r\n")
        baris = requests[0].decode() #baris pertama selalu teks

        all_headers = [n.decode() for n in requests[1:] if n]

        # Ekstrak body untuk POST
        body_index = data.find(b'\r\n\r\n') + 4
        request_body = data[body_index:]

        j = baris.split(" ")
        try:
            method = j[0].upper().strip()
            object_address = j[1].strip()

            if method == 'GET':
                return self.http_get(object_address, all_headers)
            if method == 'POST':
                # pass body and headers
                return self.http_post(object_address, all_headers, request_body)
            # PENAMBAHAN: Handling untuk method DELETE
            if method == 'DELETE':
                return self.http_delete(object_address, all_headers)
            else:
                return self.response(400, 'Bad Request', 'Metode tidak didukung', {})
        except IndexError:
            return self.response(400, 'Bad Request', '', {})

    def http_get(self, object_address, headers):
        # PENAMBAHAN: Menampilkan daftar file dan form upload jika path adalah root
        if object_address == '/':
            files = os.listdir('.') # List file di direktori saat ini
            upload_files = os.listdir(self.upload_dir) # List file di direktori upload

            response_html = "<h1>Selamat Datang di Server HTTP Sederhana</h1>"
            response_html += "<h2>File di Direktori Utama:</h2><ul>"
            for f in files:
                response_html += f"<li><a href='/{f}'>{f}</a></li>"
            response_html += "</ul>"

            response_html += f"<h2>File di Direktori {self.upload_dir}:</h2><ul>"
            for f in upload_files:
                response_html += f"<li><a href='/{self.upload_dir}{f}'>{f}</a> | <a href='#' onclick='deleteFile(\"{self.upload_dir}{f}\")'>Hapus</a></li>"

            response_html += "</ul>"

            # Form untuk upload file
            response_html += """
                <hr>
                <h2>Upload File</h2>
                <form action="/upload" enctype="multipart/form-data" method="post">
                    <input type="file" name="file" />
                    <input type="submit" value="Upload" />
                </form>

                <script>
                function deleteFile(fileName) {
                    if (confirm(`Apakah Anda yakin ingin menghapus ${fileName}?`)) {
                        fetch('/' + fileName, { method: 'DELETE' })
                            .then(response => response.text())
                            .then(data => {
                                alert(data);
                                location.reload();
                            });
                    }
                }
                </script>
            """
            return self.response(200, 'OK', response_html, {'Content-Type': 'text/html'})
        
        # Logika lama untuk menyajikan file
        object_address = object_address.strip('/')
        if os.path.isdir(object_address):
            # Jika yang diakses adalah direktori, tampilkan isinya
            files = os.listdir(object_address)
            dir_listing = f"<h1>Isi dari direktori {object_address}</h1><ul>"
            for f in files:
                dir_listing += f"<li><a href='/{os.path.join(object_address, f)}'>{f}</a></li>"
            dir_listing += "</ul><a href='../'>Kembali</a>"
            return self.response(200, 'OK', dir_listing, {'Content-Type': 'text/html'})

        if not os.path.exists(object_address):
            return self.response(404, 'Not Found', f'File {object_address} tidak ditemukan', {})

        fp = open(object_address, 'rb')
        isi = fp.read()

        fext = os.path.splitext(object_address)[1]
        content_type = self.types.get(fext, 'application/octet-stream')

        headers = {'Content-type': content_type}
        return self.response(200, 'OK', isi, headers)

    # PENAMBAHAN: method http_delete
    def http_delete(self, object_address, headers):
        object_address = object_address.strip('/')
        if not os.path.exists(object_address):
            return self.response(404, 'Not Found', 'File tidak ditemukan', {})
        
        # Pencegahan keamanan dasar: jangan biarkan menghapus di luar direktori kerja
        if '..' in object_address:
            return self.response(400, 'Bad Request', 'Path tidak valid', {})
            
        try:
            os.remove(object_address)
            return self.response(200, 'OK', f'File {object_address} berhasil dihapus', {})
        except OSError as e:
            return self.response(500, 'Internal Server Error', f'Gagal menghapus file: {e}', {})

    # PENAMBAHAN: Implementasi http_post untuk upload file
    def http_post(self, object_address, headers, body):
        if object_address == '/upload':
            # Ekstrak boundary dari header Content-Type
            content_type_header = next((h for h in headers if h.lower().startswith('content-type')), None)
            if not content_type_header:
                return self.response(400, 'Bad Request', 'Content-Type header tidak ada', {})

            try:
                boundary = content_type_header.split('; ')[1].split('=')[1]
                boundary = f'--{boundary}'.encode()
            except:
                return self.response(400, 'Bad Request', 'Boundary tidak ditemukan di Content-Type', {})
            
            # Pisahkan body berdasarkan boundary
            parts = body.split(boundary)
            # parts[0] dan parts[-1] adalah kosong atau berisi '--'
            for part in parts[1:-1]:
                if part == b'--\r\n': continue
                # Tiap part memiliki header dan content sendiri
                part_header_str, part_content = part.split(b'\r\n\r\n', 1)
                part_header_str = part_header_str.decode()
                
                # Cari nama file di header Content-Disposition
                filename_match = re.search(r'filename="([^"]+)"', part_header_str)
                if not filename_match:
                    continue
                
                filename = filename_match.group(1)
                # Hilangkan \r\n di akhir content
                if part_content.endswith(b'\r\n'):
                    part_content = part_content[:-2]

                # Simpan file
                filepath = os.path.join(self.upload_dir, os.path.basename(filename))
                with open(filepath, 'wb') as f:
                    f.write(part_content)
                
                print(f"File '{filename}' berhasil diupload ke '{filepath}'")

            return self.response(302, 'Found', '', {'Location': '/'})
        
        return self.response(404, 'Not Found', 'Endpoint POST tidak ditemukan', {})

if __name__ == "__main__":
    httpserver = HttpServer()
    # Contoh penggunaan bisa dijalankan dari server_thread_pool_http.py atau server_process_pool_http.py
    # Kode di bawah ini hanya untuk pengujian internal kelas.
    d = httpserver.proses(b'GET /testing.txt HTTP/1.0\r\n\r\n')
    print(d)
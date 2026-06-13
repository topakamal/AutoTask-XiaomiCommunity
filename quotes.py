import requests

# URL Web App Google Apps Script Anda
API_URL = "https://script.google.com/macros/s/AKfycbwJw6MCeEeRr96LRzAqsMSL7x7_0OQ4fdLui95K3PVqWqC2d1XLKDp8opCGYc51Ts72vg/exec"

def get_quote(tema="teknologi", mood="lucu", bahasa="Indonesia"):
    """
    Fungsi ini akan memanggil API dan mengembalikan (return) teks quote-nya saja.
    Bisa di-import ke file bot lain.
    """
    parameter_api = {
        "tema": tema,
        "mood": mood,
        "bahasa": bahasa
    }
    
    try:
        response = requests.get(API_URL, params=parameter_api)
        response.raise_for_status()
        data = response.json()
        
        # Jika ada error dari server Google/Gemini
        if "error" in data:
            return f"Maaf, gagal mengambil quote. Error: {data['error']}"
            
        # Mengembalikan HANYA teks quote-nya saja
        return data.get('quote', 'Quote tidak ditemukan.')
        
    except Exception as e:
        # Mengembalikan pesan error jika tidak ada internet atau URL salah
        return f"Terjadi kesalahan sistem/jaringan: {e}"

# --- BLOK TESTING ---
# Kode di bawah ini HANYA akan berjalan jika Anda menjalankan 'python quotes.py' di Termux.
# Jika file ini di-import dari file lain, kode di bawah ini TIDAK akan dieksekusi.
if __name__ == "__main__":
    print("Mengetes fungsi get_quote()...")
    hasil = get_quote(tema="teknologi", mood="lucu", bahasa="Indonesia")
    print("Output Quote:", hasil)

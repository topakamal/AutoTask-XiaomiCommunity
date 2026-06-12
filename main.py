import requests
import time
import random
import logging
import re
from datetime import datetime

# ================= KONFIGURASI UTAMA =================
SERVICE_TOKEN = "" 
DEVICE_ID = "" 
LOG_FILE = "xiaomi_global_bot_debug.log"
# =====================================================

CSRF_TOKEN = ""
C_GREEN = "\033[92m"  
C_YELLOW = "\033[93m"
C_CYAN = "\033[96m"
C_RES = "\033[0m"    

# ================= SETUP LOGGING =================
class CleanFileFormatter(logging.Formatter):
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    def format(self, record):
        formatted_message = super().format(record)
        return self.ansi_escape.sub('', formatted_message)

logger = logging.getLogger("XiaomiBot")
logger.setLevel(logging.INFO)

file_formatter = CleanFileFormatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)

stream_formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(stream_formatter)
logger.addHandler(stream_handler)
# ===============================================

def get_cookies():
    return {
        "new_bbs_serviceToken": SERVICE_TOKEN,
        "deviceId": DEVICE_ID,
        "versionCode": "500436",
        "versionName": "5.4.36"
    }

def organic_delay():
    """Memberikan jeda organik 5-10 detik sesuai permintaan"""
    jeda = round(random.uniform(5.0, 10.0), 2)
    logger.info(f"⏳ Jeda interaksi {jeda} detik...")
    time.sleep(jeda)

def generate_device_id():
    """Menghasilkan 40 karakter Hexadecimal acak untuk Device ID baru"""
    chars = "0123456789ABCDEF"
    return "".join(random.choices(chars, k=40))

def refresh_csrf_token():
    global CSRF_TOKEN
    logger.info("🔑 Menghubungkan ke server dan mengambil Data Akun...")
    url = "https://sgp-api.buy.mi.com/bbs/api/global/user/data"
    headers = {"User-Agent": "okhttp/4.12.0", "Accept": "application/json", "Host": "sgp-api.buy.mi.com"}
    try:
        res = requests.get(url, headers=headers, cookies=get_cookies(), timeout=10)
        data = res.json()
        if data.get("code") == 0:
            user_data = data.get("data", {})
            new_token = user_data.get("token")
            
            # Ekstraksi Data Profil
            user_name = user_data.get("user_name", "Unknown")
            reg_day = user_data.get("registered_day", 0)
            ip_addr = user_data.get("ip", "Unknown")
            
            level_info = user_data.get("level_info", {})
            lvl = level_info.get("level", 0)
            lvl_title = level_info.get("level_title", "Unknown")
            cur_val = level_info.get("current_value", 0)
            max_val = level_info.get("max_value", 0)
            
            if new_token:
                CSRF_TOKEN = new_token
                print("\n" + "="*50)
                logger.info(f"📊 {C_CYAN}=== DASHBOARD PROFIL PENGGUNA ==={C_RES}")
                logger.info(f"   👤 Akun       : {C_GREEN}{user_name}{C_RES}")
                logger.info(f"   🔰 Level      : {C_GREEN}{lvl} ({lvl_title}) [{cur_val}/{max_val} Poin]{C_RES}")
                logger.info(f"   🗓️ Umur Akun  : {C_GREEN}{reg_day} Hari{C_RES}")
                logger.info(f"   🌐 Alamat IP  : {C_GREEN}{ip_addr}{C_RES}")
                print("="*50 + "\n")
                return True
        elif data.get("code") == 100004:
            logger.critical("   ❌ [FATAL] Token Cookie mati atau salah! Sesi untuk akun ini gagal.")
        return False
    except Exception as e:
        logger.error(f"   ↳ Error penyegaran data: {e}")
        return False

def safe_request(method, url, json_payload=None):
    global CSRF_TOKEN
    def get_current_headers():
        return {
            "User-Agent": "okhttp/4.12.0", "Accept": "application/json",
            "Content-Type": "application/json; charset=utf-8", "Host": "sgp-api.buy.mi.com",
            "x-csrf-token": CSRF_TOKEN, "x-requested-with": "com.mi.global.bbs",
            "referer": "https://new.c.mi.com/"
        }
    try:
        if method.upper() == "GET":
            res = requests.get(url, headers=get_current_headers(), cookies=get_cookies(), timeout=10)
        else:
            res = requests.post(url, headers=get_current_headers(), cookies=get_cookies(), json=json_payload, timeout=10)
            
        if res.json().get("code") == 100004:
            logger.warning("   ⚠️ Token CSRF expired. Pemulihan otomatis berjalan...")
            if refresh_csrf_token():
                logger.info("   🔄 Menembak ulang request dengan token baru...")
                if method.upper() == "GET":
                    res = requests.get(url, headers=get_current_headers(), cookies=get_cookies(), timeout=10)
                else:
                    res = requests.post(url, headers=get_current_headers(), cookies=get_cookies(), json=json_payload, timeout=10)
        return res
    except Exception as e:
        logger.error(f"   ↳ Error Koneksi: {e}")
        return None

# --- FUNGSI ANALISIS & KLAIM ---

def get_task_status():
    logger.info("🔍 Menganalisis status tugas harian...")
    url = "https://sgp-api.buy.mi.com/bbs/api/global/task/list"
    res = safe_request("GET", url)
    status_dict = {}
    
    if res and res.json().get("code") == 0:
        logger.info(f"   ↳ Respons: {C_GREEN}Berhasil Memuat Data{C_RES}")
        for task in res.json().get("data", {}).get("list", []):
            t_id = task.get("task_id")
            if t_id == 2: continue 
            
            total = task.get("total")
            finish = task.get("finish")
            status_dict[t_id] = {
                "total": total,
                "finish": finish,
                "remaining": max(0, total - finish)
            }
        return status_dict
    else:
        logger.error("❌ Gagal membaca status tugas.")
        return {}

def claim_task(task_id, silent=False):
    if not silent:
        logger.info(f"🎁 Mengklaim Poin untuk Task ID: {task_id}...")
        
    url_finish = "https://sgp-api.buy.mi.com/bbs/api/global/task/finish"
    payload = {"task_id": task_id}
    res = safe_request("POST", url_finish, payload)
    
    if res:
        data = res.json()
        if data.get("code") == 0:
            if silent:
                logger.info(f"🎁 [SAPU BERSIH] Poin Task ID {task_id} yang tertinggal berhasil diamankan!")
            logger.info(f"   ↳ Respons Klaim: {C_GREEN}{res.text}{C_RES}")
            return True
        elif data.get("code") == 100003:
            if not silent:
                logger.info(f"   ↳ Respons: {C_GREEN}Poin sudah diklaim sebelumnya (100003){C_RES}")
            return False
        else:
            if not silent:
                logger.info(f"   ↳ Respons Klaim: {C_YELLOW}{res.text}{C_RES}")
    return False

def show_task_list():
    print("\n" + "="*50)
    logger.info("📋 DAFTAR STATUS TUGAS HARIAN (FINAL)")
    url_list = "https://sgp-api.buy.mi.com/bbs/api/global/task/list"
    res = safe_request("GET", url_list)
    if res and res.json().get("code") == 0:
        task_names = {
            1: "Lihat Postingan", 2: "Membuat Post (Skip)",
            4: "Menyukai Post", 6: "Membuat Komentar",
            7: "Menyukai Komentar", 8: "Check-in Harian",
            11: "Mengikuti User"
        }
        for task in res.json().get("data", {}).get("list", []):
            t_id = task.get("task_id")
            name = task_names.get(t_id, f"Tugas {t_id}")
            logger.info(f" ▪️ {name:<24} : {task.get('finish')}/{task.get('total')}")
    print("="*50)

# --- FUNGSI EKSEKUSI TUGAS ORGANIK ---

def do_check_in():
    logger.info("📅 Eksekusi: Check-in Harian...")
    url = f"https://sgp-api.buy.mi.com/bbs/api/global/user/check-in?year={datetime.now().year}&month={datetime.now().month}"
    res = safe_request("GET", url)
    if res: logger.info(f"   ↳ Respons: {C_GREEN}{res.text}{C_RES}")
    organic_delay()

def get_featured_posts():
    url = "https://sgp-api.buy.mi.com/bbs/api/global/featured-post/list?limit=10&after="
    res = safe_request("GET", url)
    if res and res.json().get("code") == 0:
        return [post.get("post_id") for post in res.json().get("data", [])]
    return []

def follow_random_user_from_post(post_id):
    logger.info(f"👤 Mencari pengguna aktif di Post ID {post_id}...")
    url_list = f"https://sgp-api.buy.mi.com/bbs/api/global/comment/list?aid={post_id}&limit=10&after=&sort_type=2"
    res_list = safe_request("GET", url_list)
    if res_list and res_list.json().get("code") == 0:
        comments = res_list.json().get("data", {}).get("list", [])
        if comments:
            target_user_id = random.choice(comments).get("comment_user_id")
            logger.info(f"   ↳ Menemukan User ID {target_user_id[:8]}... Mengikuti...")
            url_follow = "https://sgp-api.buy.mi.com/bbs/api/global/user/follow"
            payload = {"follow_user_id": target_user_id, "follow_type": 1}
            res_follow = safe_request("POST", url_follow, payload)
            if res_follow: 
                logger.info(f"   ↳ Respons: {C_GREEN}{res_follow.text}{C_RES}")
                return True
        else:
            logger.warning("   ⚠️ Tidak ada pengguna di kolom komentar ini. Lewati.")
    return False

def read_post(post_id):
    logger.info(f"📖 Membaca Post ID: {post_id}...")
    url = f"https://sgp-api.buy.mi.com/bbs/api/global/text/info?aid={post_id}"
    res = safe_request("GET", url)
    if res: 
        try:
            json_resp = f'{{"code":{res.json().get("code")}, "msg":"{res.json().get("msg")}"}}'
            logger.info(f"   ↳ Respons: {C_GREEN}{json_resp}{C_RES}")
        except: pass
    organic_delay()

def like_post(post_id):
    logger.info(f"❤️ Menyukai Post ID: {post_id}...")
    url = "https://sgp-api.buy.mi.com/bbs/api/global/action/like"
    payload = {"aid": int(post_id), "action": True}
    res = safe_request("POST", url, payload)
    if res: logger.info(f"   ↳ Respons: {C_GREEN}{res.text}{C_RES}")
    organic_delay()

def comment_post(post_id):
    logger.info(f"💬 Mengomentari Post ID: {post_id}...")
    url = "https://sgp-api.buy.mi.com/bbs/api/global/comment/add"
    komentar_list = ["Nice info!", "Good job", "Great thread", "Thanks for sharing!", "Awesome!", "Very helpful, thanks!"]
    payload = {"text": random.choice(komentar_list), "blocks": "", "aid": int(post_id)}
    res = safe_request("POST", url, payload)
    if res: logger.info(f"   ↳ Respons: {C_GREEN}{res.text}{C_RES}")
    organic_delay()

def like_other_comment(post_id):
    logger.info(f"👍 Mencari komentar pengguna lain untuk di-like...")
    url_list = f"https://sgp-api.buy.mi.com/bbs/api/global/comment/list?aid={post_id}&limit=10&after=&sort_type=2&comment_id=&first_comment_id="
    res_list = safe_request("GET", url_list)
    if res_list and res_list.json().get("code") == 0:
        comments = res_list.json().get("data", {}).get("list", [])
        if comments:
            comment_id = random.choice(comments).get("comment_id")
            logger.info(f"   ↳ Menemukan Komentar ID {comment_id[-6:]}... Menyukai...")
            url_like = "https://sgp-api.buy.mi.com/bbs/api/global/comment/support"
            payload_like = {"aid": int(post_id), "comment_id": comment_id, "operation_action": 1}
            res_like = safe_request("POST", url_like, payload_like)
            if res_like: 
                logger.info(f"   ↳ Respons: {C_GREEN}{res_like.text}{C_RES}")
        else:
            logger.warning("   ⚠️ Kolom komentar kosong. Lewati.")
    organic_delay()

# --- ALUR UTAMA PROGRAM ---

def main():
    global SERVICE_TOKEN, DEVICE_ID, CSRF_TOKEN
    logger.info("=== 🤖 Memulai Bot Auto-Task V8.6 (Smart Multi-Account) ===")
    
    # 0. Setup File Input
    print("\n" + "="*50)
    file_path = input("📂 Masukkan nama file text daftar akun (contoh: akun.txt): ").strip()
    print("="*50 + "\n")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            lines = [line.strip() for line in file.readlines() if line.strip()]
            logger.info(f"✅ Berhasil memuat {len(lines)} baris data dari '{file_path}'")
    except FileNotFoundError:
        logger.critical(f"❌ File '{file_path}' tidak ditemukan! Pastikan file berada di folder yang sama.")
        return

    # Loop melalui setiap baris akun di dalam file
    for index, line in enumerate(lines, 1):
        print("\n" + "#"*60)
        logger.info(f"🚀 MEMPROSES AKUN KE-{index} DARI {len(lines)}")
        print("#"*60)

        # Cek apakah ada separator "|" untuk Device ID
        parts = line.split('|')
        SERVICE_TOKEN = parts[0].strip()
        CSRF_TOKEN = "" # Reset CSRF Token
        
        # Logika Autentikasi Device ID Baru
        if len(parts) >= 2 and parts[1].strip():
            DEVICE_ID = parts[1].strip()
        else:
            DEVICE_ID = generate_device_id()
            logger.info(f"   ⚙️ Device ID tidak ditemukan. Membuat ID acak: {C_CYAN}{DEVICE_ID}{C_RES}")

        if not SERVICE_TOKEN:
            logger.warning(f"⚠️ Token kosong pada baris ke-{index}. Melewati...")
            continue
            
        if not refresh_csrf_token():
            logger.warning(f"⏭️ Gagal memuat data pengguna untuk akun ke-{index}. Melewati...")
            continue
        
        tasks = get_task_status()
        if not tasks: 
            logger.warning(f"⏭️ Gagal memuat daftar tugas untuk akun ke-{index}. Melewati...")
            continue

        # 1. Sapu Bersih Klaim Lama
        has_silent_claims = False
        for t_id, t_data in tasks.items():
            if t_data["remaining"] == 0:
                if claim_task(t_id, silent=True):
                    has_silent_claims = True
        if has_silent_claims: print("-" * 50)

        # 2. Eksekusi Check-in
        if tasks.get(8, {}).get("remaining", 0) > 0:
            do_check_in()
            claim_task(8, silent=False) 

        post_ids = get_featured_posts()
        if not post_ids:
            logger.error("❌ Gagal memuat postingan beranda untuk interaksi.")
            continue

        # 3. Eksekusi Follow Secara Sequential
        t11_data = tasks.get(11, {})
        rem_11 = t11_data.get("remaining", 0)
        fin_11 = t11_data.get("finish", 0)
        tot_11 = t11_data.get("total", 0)

        if rem_11 > 0:
            logger.info(f"▶️ Mengeksekusi Task Follow: Kurang {rem_11} lagi...")
            for pid in reversed(post_ids): 
                if rem_11 <= 0: break
                if follow_random_user_from_post(pid):
                    fin_11 += 1
                    rem_11 -= 1
                    logger.info(f"   ↳ Progres Task Follow: ({fin_11}/{tot_11})")
                    claim_task(11, silent=False) 
                    organic_delay()

        # 4. Eksekusi Interaksi Postingan Secara Sequential
        t1_data = tasks.get(1, {}); rem_1 = t1_data.get("remaining", 0); fin_1 = t1_data.get("finish", 0); tot_1 = t1_data.get("total", 0)
        t4_data = tasks.get(4, {}); rem_4 = t4_data.get("remaining", 0); fin_4 = t4_data.get("finish", 0); tot_4 = t4_data.get("total", 0)
        t6_data = tasks.get(6, {}); rem_6 = t6_data.get("remaining", 0); fin_6 = t6_data.get("finish", 0); tot_6 = t6_data.get("total", 0)
        t7_data = tasks.get(7, {}); rem_7 = t7_data.get("remaining", 0); fin_7 = t7_data.get("finish", 0); tot_7 = t7_data.get("total", 0)

        max_post = max(rem_1, rem_4, rem_6, rem_7)
        if max_post > 0:
            logger.info(f"▶️ Mengeksekusi interaksi postingan. Membutuhkan {max_post} post...")
            for i in range(max_post):
                if i >= len(post_ids): break
                pid = post_ids[i]
                
                if rem_1 > 0:
                    read_post(pid)
                    fin_1 += 1
                    rem_1 -= 1
                    logger.info(f"   ↳ Progres Baca Post: ({fin_1}/{tot_1})")
                    claim_task(1, silent=False)

                if rem_4 > 0:
                    like_post(pid)
                    fin_4 += 1
                    rem_4 -= 1
                    logger.info(f"   ↳ Progres Like Post: ({fin_4}/{tot_4})")
                    claim_task(4, silent=False) 

                if rem_6 > 0:
                    comment_post(pid)
                    fin_6 += 1
                    rem_6 -= 1
                    logger.info(f"   ↳ Progres Komentar: ({fin_6}/{tot_6})")
                    claim_task(6, silent=False) 

                if rem_7 > 0:
                    like_other_comment(pid)
                    fin_7 += 1
                    rem_7 -= 1
                    logger.info(f"   ↳ Progres Like Komentar: ({fin_7}/{tot_7})")
                    claim_task(7, silent=False)

                if i < (max_post - 1): 
                    print("-" * 50)

        # 5. Laporan Akhir Akun
        show_task_list()
        
    logger.info("\n=== 🎉 SELURUH SIKLUS MULTI-AKUN TELAH OPTIMAL SELESAI ===")

if __name__ == "__main__":
    main()

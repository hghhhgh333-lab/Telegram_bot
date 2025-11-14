
# -*- coding: utf-8 -*-
import os
import math
import telebot
from pykml import parser
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup
import re
import zipfile
import shutil

# ==================== استخراج الملفات من الأرشيف ====================

def extract_bot_files():
    """استخراج الملفات من الأرشيف إذا لزم الأمر"""
    zip_file = "telegram-bot.zip"
    
    # إذا كانت الملفات غير موجودة ولكن الأرشيف موجود
    if (not os.path.exists("my_kml_files") or not os.listdir("my_kml_files")) and os.path.exists(zip_file):
        print("📦 جاري استخراج الملفات من الأرشيف...")
        
        try:
            # استخراج الأرشيف
            with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                zip_ref.extractall(".")
            print("✅ تم استخراج الملفات بنجاح")
        except Exception as e:
            print(f"❌ خطأ في استخراج الملفات: {e}")
    else:
        print("✅ الملفات موجودة وجاهزة")

# استدعاء استخراج الملفات عند البدء
extract_bot_files()

# ==================== الكود الأصلي (بدون تعديل) ====================

# ضع التوكن الخاص بالبوت هنا (لا تشاركه علنيا)
TOKEN = "8092728497:AAGw58Y6IPmmjL74iA0NMes2tkCFIvuSPAA"

# مسار المجلد الذي يحتوي على ملفات KML
KML_DIR = "my_kml_files"

# تهيئة البوت
bot = telebot.TeleBot(TOKEN, parse_mode="Markdown")

# متغيرات حالة المستخدم
user_state = {}  # مثال: {chat_id: {"service": "search_fat", "zone_selected": ..., "fats": {...}}}

# الكلمات المفتاحية للبدء
start_keywords = ["ابدأ", "ابدا", "تشغيل", "/start"]

# ==================== دوال مساعدة ====================

def numeric_key(text: str) -> int:
    digits = "".join(ch for ch in text if ch.isdigit())
    return int(digits) if digits else 0

def read_kml(path):
    with open(path, "r", encoding="utf-8") as f:
        return parser.parse(f).getroot()

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi, dlambda = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))

def find_fat_id(placemark, ns):
    # البحث عن FAT_ID بطرق متعددة
    for sd in placemark.findall('.//kml:SimpleData', ns):
        if sd.text and sd.attrib.get('name') == "FAT_ID":
            return sd.text.strip()
    extended_data = placemark.find('.//kml:ExtendedData', ns)
    if extended_data is not None:
        for data in extended_data.findall('.//kml:Data', ns):
            if data.get('name') == "FAT_ID":
                value_elem = data.find('.//kml:value', ns)
                if value_elem is not None and value_elem.text:
                    return value_elem.text.strip()
    name_elem = placemark.find('.//kml:name', ns)
    if name_elem is not None and name_elem.text:
        name_text = name_elem.text.strip()
        if "FAT" in name_text.upper():
            return name_text
    return "بدون اسم"

def find_coordinates(placemark, ns):
    # البحث عن الإحداثيات من Point أو Polygon
    coord_elem = placemark.find('.//kml:Point/kml:coordinates', ns)
    if coord_elem is not None and coord_elem.text:
        return coord_elem.text.strip()
    poly_elem = placemark.find('.//kml:Polygon/kml:outerBoundaryIs/kml:LinearRing/kml:coordinates', ns)
    if poly_elem is not None and poly_elem.text:
        coords_text = poly_elem.text.strip()
        coords_list = []
        for c in coords_text.split():
            parts = [x.strip() for x in c.split(',')]
            if len(parts) >= 2:
                try:
                    lon, lat = float(parts[0]), float(parts[1])
                    coords_list.append((lat, lon))
                except ValueError:
                    continue
        if coords_list:
            avg_lat = sum(p[0] for p in coords_list) / len(coords_list)
            avg_lon = sum(p[1] for p in coords_list) / len(coords_list)
            return f"{avg_lon},{avg_lat}"
    return None

def read_fats_with_regex(content):
    """استخراج FATs باستخدام regex إذا فشل التحليل العادي"""
    fats = {}
    placemark_pattern = r'<Placemark[^>]*>(.*?)</Placemark>'
    placemark_matches = re.findall(placemark_pattern, content, re.DOTALL | re.IGNORECASE)
    for i, placemark_content in enumerate(placemark_matches):
        fat_id = "FAT_" + str(i+1)
        simple_data_pattern = r'<SimpleData name="FAT_ID"[^>]*>(.*?)</SimpleData>'
        simple_match = re.search(simple_data_pattern, placemark_content, re.IGNORECASE)
        if simple_match:
            fat_id = simple_match.group(1).strip()
        else:
            data_pattern = r'<Data name="FAT_ID"[^>]*>.*?<value[^>]*>(.*?)</value>'
            data_match = re.search(data_pattern, placemark_content, re.IGNORECASE | re.DOTALL)
            if data_match:
                fat_id = data_match.group(1).strip()
            else:
                name_pattern = r'<name[^>]*>(.*?)</name>'
                name_match = re.search(name_pattern, placemark_content, re.IGNORECASE)
                if name_match and "FAT" in name_match.group(1).upper():
                    fat_id = name_match.group(1).strip()
        coord = None
        point_pattern = r'<Point>.*?<coordinates[^>]*>(.*?)</coordinates>'
        point_match = re.search(point_pattern, placemark_content, re.IGNORECASE | re.DOTALL)
        if point_match:
            coord = point_match.group(1).strip()
        else:
            polygon_pattern = r'<Polygon>.*?<coordinates[^>]*>(.*?)</coordinates>'
            polygon_match = re.search(polygon_pattern, placemark_content, re.IGNORECASE | re.DOTALL)
            if polygon_match:
                coords_text = polygon_match.group(1).strip()
                coords_list = []
                for c in coords_text.split():
                    parts = [x.strip() for x in c.split(',')]
                    if len(parts) >= 2:
                        try:
                            lon, lat = float(parts[0]), float(parts[1])
                            coords_list.append((lat, lon))
                        except ValueError:
                            continue
                if coords_list:
                    avg_lat = sum(p[0] for p in coords_list) / len(coords_list)
                    avg_lon = sum(p[1] for p in coords_list) / len(coords_list)
                    coord = f"{avg_lon},{avg_lat}"
        if coord:
            fats[fat_id] = coord
    return fats

def read_fats_from_file(filename):
    path = os.path.join(KML_DIR, filename)
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
    except:
        return {}
    fats = {}
    ns = {'kml': 'http://www.opengis.net/kml/2.2'}
    try:
        root = parser.fromstring(content)
    except:
        return read_fats_with_regex(content)
    for placemark in root.findall('.//kml:Placemark', ns):
        fat_id = find_fat_id(placemark, ns)
        coord = find_coordinates(placemark, ns)
        if fat_id != "بدون اسم" and coord:
            fats[fat_id] = coord
    return fats

def send_coord(chat_id, fat_id, coord):
    lon, lat = [c.strip() for c in coord.split(',')][:2]
    map_link = f"http://maps.google.com/maps?q={lat},{lon}"
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("رجوع", callback_data="start_bot"))
    message_text = (
        f"📍 FAT *{fat_id}*:\n"
        f"خط الطول: `{lon}`\n"
        f"خط العرض: `{lat}`\n"
        f"[🗺️ Google Maps]({map_link})"
    )
    bot.send_message(chat_id, message_text, parse_mode="Markdown", reply_markup=kb)

# ==================== وظائف البدء والخدمات ====================

@bot.message_handler(func=lambda m: isinstance(m.text, str) and any(word in m.text.lower() for word in start_keywords))
def show_start_button(msg):
    chat_id = msg.chat.id
    user_state[chat_id] = {}
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("ابدأ البوت", callback_data="start_bot"))
    bot.send_message(chat_id, "أهلاً! اضغط على الزر أدناه للبدء:", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data == "start_bot")
def start_bot(call):
    chat_id = call.message.chat.id
    try:
        bot.edit_message_text("اختر الخدمة التي تريدها:", chat_id, call.message.message_id)
    except:
        bot.send_message(chat_id, "اختر الخدمة التي تريدها:")
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("البحث عن FAT", callback_data="service_search_fat"))
    kb.add(InlineKeyboardButton("إرسال الموقع لأقرب 3 FATs", callback_data="service_nearby"))
    kb.add(InlineKeyboardButton("البحث عبر الإحداثيات", callback_data="service_by_coords"))
    bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("service_"))
def service_selected(call):
    chat_id = call.message.chat.id
    data = call.data

    kb_back = InlineKeyboardMarkup(row_width=1)
    kb_back.add(InlineKeyboardButton("رجوع", callback_data="start_bot"))

    if data == "service_search_fat":
        user_state[chat_id] = {"service": "search_fat"}
        bot.send_message(chat_id, "ارسل رقم الزون للبحث عنه:", reply_markup=kb_back)
    elif data == "service_nearby":
        user_state[chat_id] = {"service": "nearby"}
        bot.send_message(chat_id, "الرجاء ارسال موقعك لتحديد أقرب 3 FATs:", reply_markup=kb_back)
    elif data == "service_by_coords":
        user_state[chat_id] = {"service": "by_coords"}
        bot.send_message(chat_id, "ارسل الإحداثية بهذا الشكل:\n`35.518362,44.389652`", parse_mode="Markdown", reply_markup=kb_back)

    bot.answer_callback_query(call.id)

# ==================== التعامل مع النصوص ====================

@bot.message_handler(func=lambda m: True)
def handle_text(msg):
    if not isinstance(msg.text, str):
        return
    chat_id = msg.chat.id
    text = msg.text.strip()
    state = user_state.get(chat_id, {})

    kb_back = InlineKeyboardMarkup(row_width=1)
    kb_back.add(InlineKeyboardButton("رجوع", callback_data="start_bot"))

    # ------------------ حالة: البحث عبر الإحداثيات ------------------
    if state.get("service") == "by_coords":
        coord_match = re.match(r"^\s*(-?\d+(?:\.\d+)?),\s*(-?\d+(?:\.\d+)?)\s*$", text)
        if not coord_match:
            bot.send_message(chat_id, "صيغة الإحداثية غير صحيحة.\nيرجى الإرسال بهذا الشكل:\n`35.518362,44.389652`", parse_mode="Markdown", reply_markup=kb_back)
            return

        lat = float(coord_match.group(1))
        lon = float(coord_match.group(2))
        bot.send_message(chat_id, "جاري البحث عن أقرب FAT ...")

        points = []
        ns = {'kml': 'http://www.opengis.net/kml/2.2'}

        for filename in os.listdir(KML_DIR):
            if not filename.lower().endswith(".kml"):
                continue
            path = os.path.join(KML_DIR, filename)
            try:
                root = read_kml(path)
            except:
                continue

            for placemark in root.findall('.//kml:Placemark', ns):
                name = "غير معروف"
                for sd in placemark.findall('.//kml:SimpleData', ns):
                    if sd.attrib.get('name') == "FAT_ID" and sd.text:
                        name = sd.text.strip()

                coord = find_coordinates(placemark, ns)
                if coord:
                    lon_f, lat_f = [float(c.strip()) for c in coord.split(',')[:2]]
                    dist = haversine(lat, lon, lat_f, lon_f)
                    points.append((filename, name, lat_f, lon_f, dist))

        if not points:
            bot.send_message(chat_id, "لم يتم العثور على أي FATs في الملفات.", reply_markup=kb_back)
            return

        points.sort(key=lambda x: x[4])
        nearest = points[0]
        zone, fat_name, lat_f, lon_f, dist = nearest
        map_link = f"http://maps.google.com/maps?q={lat_f},{lon_f}"

        bot.send_message(
            chat_id,
            f"أقرب FAT من الإحداثية المرسلة:\n"
            f"*{fat_name}* — `{dist:.2f}` كم\n"
            f"Zone: `{zone}`\n"
            f"[Google Maps]({map_link})",
            parse_mode="Markdown",
            reply_markup=kb_back
        )
        return

    # ------------------ حالة: البحث عن FAT ------------------
    if state.get("service") == "search_fat":
        # 1) اذا ما تم اختيار الزون بعد
        if not state.get("zone_selected"):
            try:
                files = [f for f in os.listdir(KML_DIR) if f.lower().endswith(".kml")]
            except Exception as e:
                bot.send_message(chat_id, f"خطأ في الوصول للمجلد: {e}", reply_markup=kb_back)
                return

            matches = [f for f in files if str(numeric_key(text)) in str(numeric_key(f))]

            if not matches:
                bot.send_message(chat_id, "لم يتم العثور على أي زون مطابق.", reply_markup=kb_back)
                return

            if len(matches) == 1:
                filename = matches[0]
                fats = read_fats_from_file(filename)
                user_state[chat_id].update({"zone_selected": filename, "fats": fats})
                bot.send_message(chat_id, f"تم اختيار الزون: *{filename}*\nالآن ارسل رقم FAT للبحث عنه:", parse_mode="Markdown", reply_markup=kb_back)
                return

            kb = InlineKeyboardMarkup(row_width=1)
            for f in matches:
                kb.add(InlineKeyboardButton(f, callback_data=f"select_zone::{f}"))
            kb.add(InlineKeyboardButton("رجوع", callback_data="start_bot"))
            bot.send_message(chat_id, "اختر الزون الصحيح:", reply_markup=kb)
            return

        # 2) تم اختيار الزون لكن لم يتم اختيار FAT بعد
        if state.get("zone_selected") and not state.get("fat_selected"):
            fats = state.get("fats", {})
            matches = [f for f in fats.keys() if str(numeric_key(text)) in str(numeric_key(f))]

            if not matches:
                bot.send_message(chat_id, "لم يتم العثور على أي FAT مطابق في هذا الزون.", reply_markup=kb_back)
                return

            if len(matches) == 1:
                fat_id = matches[0]
                coord = fats[fat_id]
                user_state[chat_id].update({"fat_selected": fat_id})
                send_coord(chat_id, fat_id, coord)
                return

            kb = InlineKeyboardMarkup(row_width=1)
            for f in matches:
                kb.add(InlineKeyboardButton(f, callback_data=f"select_fat::{f}"))
            kb.add(InlineKeyboardButton("رجوع", callback_data="start_bot"))
            bot.send_message(chat_id, "اختر FAT الصحيح:", reply_markup=kb)
            return

    # إذا لم تكن أي خدمة مختارة
    if not state.get("service"):
        kb = InlineKeyboardMarkup(row_width=1)
        kb.add(InlineKeyboardButton("ابدأ البوت", callback_data="start_bot"))
        bot.send_message(chat_id, "لم يتم اختيار خدمة. اضغط ابدأ للاختيار.", reply_markup=kb)
        return

# ==================== التعامل مع أزرار الاختيار (Callbacks) ====================

@bot.callback_query_handler(func=lambda c: c.data.startswith("select_zone::"))
def zone_selected(call):
    chat_id = call.message.chat.id
    filename = call.data.split("::", 1)[1]

    fats = read_fats_from_file(filename)
    user_state.setdefault(chat_id, {}).update({"zone_selected": filename, "fats": fats})
    try:
        bot.edit_message_text(f"تم اختيار الزون: *{filename}*\nالآن ارسل رقم FAT للبحث عنه:", chat_id, call.message.message_id, parse_mode="Markdown")
    except:
        bot.send_message(chat_id, f"تم اختيار الزون: *{filename}*\nالآن ارسل رقم FAT للبحث عنه:", parse_mode="Markdown")
    bot.answer_callback_query(call.id, text=f"تم اختيار: {filename}")

@bot.callback_query_handler(func=lambda c: c.data.startswith("select_fat::"))
def fat_selected(call):
    chat_id = call.message.chat.id
    fat_id = call.data.split("::", 1)[1]
    st = user_state.get(chat_id)

    if not st or "fats" not in st:
        try:
            bot.edit_message_text("حدث خطأ أو انتهت الجلسة، يرجى إعادة المحاولة.", chat_id, call.message.message_id)
        except:
            bot.send_message(chat_id, "حدث خطأ أو انتهت الجلسة، يرجى إعادة المحاولة.")
        return

    coord = st["fats"].get(fat_id)
    if not coord:
        try:
            bot.edit_message_text("لم يتم العثور على الإحداثيات.", chat_id, call.message.message_id)
        except:
            bot.send_message(chat_id, "لم يتم العثور على الإحداثيات.")
        return

    user_state[chat_id].update({"fat_selected": fat_id})
    send_coord(chat_id, fat_id, coord)
    bot.answer_callback_query(call.id, text=f"تم اختيار: {fat_id}")

# ==================== التعامل مع الموقع لأقرب 3 FATs ====================

@bot.message_handler(content_types=['location'])
def handle_location(msg):
    chat_id = msg.chat.id
    state = user_state.get(chat_id)

    if not state or state.get("service") != "nearby":
        bot.send_message(chat_id, "لم يتم اختيار خدمة البحث عن أقرب FATs، استخدم زر 'ابدأ' للمتابعة.")
        return

    user_lat, user_lon = msg.location.latitude, msg.location.longitude
    points = []
    ns = {'kml': 'http://www.opengis.net/kml/2.2'}

    for filename in os.listdir(KML_DIR):
        if not filename.lower().endswith(".kml"):
            continue
        path = os.path.join(KML_DIR, filename)
        try:
            root = read_kml(path)
        except:
            continue

        for placemark in root.findall('.//kml:Placemark', ns):
            name = "غير معروف"
            for sd in placemark.findall('.//kml:SimpleData', ns):
                if sd.attrib.get('name') == "FAT_ID" and sd.text:
                    name = sd.text.strip()

            coord = find_coordinates(placemark, ns)
            if coord:
                lon_str, lat_str = [c.strip() for c in coord.split(',')][:2]
                lat, lon = float(lat_str), float(lon_str)
                dist = haversine(user_lat, user_lon, lat, lon)
                points.append((filename, name, lat, lon, dist))

    if not points:
        bot.send_message(chat_id, "لم يتم العثور على أي نقاط (FATs) في ملفات KML.")
        return

    points.sort(key=lambda x: x[4])
    top3 = points[:3]

    text = "أقرب 3 نقاط FAT من موقعك:\n\n"
    for i, (zone, name, lat, lon, dist) in enumerate(top3, 1):
        map_link = f"http://maps.google.com/maps?q={lat},{lon}"
        text += (
            f"{i}. *{name}* — `{dist:.2f}` كم\n"
            f"Zone: `{zone}`\n"
            f"[Google Maps]({map_link})\n\n"
        )

    bot.send_message(chat_id, text, parse_mode="Markdown")

# ==================== بدء تشغيل البوت ====================

if __name__ == '__main__':
    if not os.path.isdir(KML_DIR):
        print(f"تنبيه: لم يتم العثور على المجلد {KML_DIR}. يرجى إنشاؤه ووضع ملفات KML فيه.")
    print("البوت يعمل الآن. اضغط على CTRL+C للإيقاف.")
    bot.polling(none_stop=True)
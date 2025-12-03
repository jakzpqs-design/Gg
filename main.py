from flask import Flask, request, jsonify, render_template
from datetime import datetime
import json

app = Flask(__name__)

# ملف لحفظ السجلات
LOG_FILE = 'access_logs.json'
BOTS_FILE = 'bots_status.json'

def log_request():
    """تسجيل تفاصيل الطلب"""
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'method': request.method,
        'path': request.path,
        'ip_address': request.remote_addr,
        'user_agent': request.headers.get('User-Agent'),
        'headers': dict(request.headers),
        'query_params': dict(request.args),
        'form_data': dict(request.form),
        'json_data': request.get_json(silent=True),
        'data': request.get_data(as_text=True)
    }
    
    # قراءة السجلات الموجودة
    try:
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            logs = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        logs = []
    
    # إضافة السجل الجديد
    logs.append(log_entry)
    
    # حفظ السجلات
    with open(LOG_FILE, 'w', encoding='utf-8') as f:
        json.dump(logs, f, ensure_ascii=False, indent=2)
    
    return log_entry

def update_bots_from_logs():
    """قراءة اللوج الرئيسي واستخراج بيانات البوتات"""
    try:
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            logs = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    
    bots_data = {}
    
    # معالجة جميع السجلات لاستخراج بيانات البوتات
    for log_entry in logs:
        json_data = log_entry.get('json_data')
        if not json_data:
            continue
        
        event_type = json_data.get('event')
        
        # معالجة حدث اتصال البوت
        if event_type == 'bot_connected':
            bot_name = json_data.get('bot_name', 'unknown')
            bots_data[bot_name] = {
                'status': json_data.get('status', 'online'),
                'device_name': json_data.get('device_name'),
                'device_type': json_data.get('device_type'),
                'user_id': json_data.get('user_id'),
                'room_id': json_data.get('room_id'),
                'last_seen': log_entry.get('timestamp')
            }
        
        # معالجة حدث بدء النظام
        elif event_type == 'system_startup':
            started_bots = json_data.get('started_bots', [])
            for bot in started_bots:
                bot_name = bot.get('name', 'unknown')
                bots_data[bot_name] = {
                    'status': 'online',
                    'owner': bot.get('owner'),
                    'room_id': bot.get('room_id'),
                    'device_type': 'bot',
                    'last_seen': log_entry.get('timestamp')
                }
        
        # معالجة بيانات الفحص الصحي
        elif event_type == 'health_check':
            health_data = json_data.get('health_check_data', {})
            
            # البوتات السليمة
            healthy_bots = health_data.get('healthy_bots', [])
            for bot in healthy_bots:
                bot_name = bot.get('name', 'unknown')
                bots_data[bot_name] = {
                    'status': 'online',
                    'owner': bot.get('owner'),
                    'heartbeat_age': bot.get('heartbeat_age'),
                    'device_type': 'bot',
                    'last_seen': log_entry.get('timestamp')
                }
            
            # البوتات المعاد تشغيلها
            restarted_bots = health_data.get('restarted_bots', [])
            for bot in restarted_bots:
                bot_name = bot.get('name', 'unknown')
                bots_data[bot_name] = {
                    'status': 'restarted',
                    'owner': bot.get('owner'),
                    'device_type': 'bot',
                    'last_seen': log_entry.get('timestamp')
                }
            
            # البوتات الفاشلة
            failed_bots = health_data.get('failed_bots', [])
            for bot in failed_bots:
                bot_name = bot.get('name', 'unknown')
                bots_data[bot_name] = {
                    'status': 'failed',
                    'owner': bot.get('owner'),
                    'device_type': 'bot',
                    'last_seen': log_entry.get('timestamp')
                }
            
            # البوتات المتوقفة
            stopped_bots = health_data.get('stopped_bots', [])
            for bot in stopped_bots:
                bot_name = bot.get('name', 'unknown')
                bots_data[bot_name] = {
                    'status': 'offline',
                    'owner': bot.get('owner'),
                    'device_type': 'bot',
                    'last_seen': log_entry.get('timestamp')
                }
    
    # حفظ بيانات البوتات
    with open(BOTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(bots_data, f, ensure_ascii=False, indent=2)
    
    return bots_data

@app.route('/', methods=['GET'])
def index():
    """الصفحة الرئيسية - عرض واجهة الويب"""
    response = app.make_response(render_template('index.html'))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route('/webhook/bot_data', methods=['POST'])
@app.route('/webhook/bot_status', methods=['POST'])
def receive_bot_data():
    """استقبال بيانات البوتات فقط"""
    log_entry = log_request()
    
    # تحديث بيانات البوتات فوراً بعد الاستلام
    update_bots_from_logs()
    
    return jsonify({
        'status': 'success',
        'message': 'تم استلام البيانات بنجاح',
        'received_at': log_entry['timestamp']
    }), 200

@app.route('/api/bots', methods=['GET'])
def get_bots():
    """API لعرض البوتات المتصلة"""
    # تحديث بيانات البوتات من اللوج الرئيسي
    bots_data = update_bots_from_logs()
    
    return jsonify({
        'status': 'success',
        'total': len(bots_data),
        'bots': bots_data
    }), 200

@app.route('/logs', methods=['GET'])
def get_logs():
    """عرض جميع السجلات"""
    try:
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            logs = json.load(f)
        return jsonify({
            'total_logs': len(logs),
            'logs': logs
        }), 200
    except FileNotFoundError:
        return jsonify({
            'total_logs': 0,
            'logs': []
        }), 200

@app.route('/logs/clear', methods=['POST'])
def clear_logs():
    """مسح جميع السجلات"""
    with open(LOG_FILE, 'w', encoding='utf-8') as f:
        json.dump([], f)
    return jsonify({
        'status': 'success',
        'message': 'تم مسح جميع السجلات'
    }), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

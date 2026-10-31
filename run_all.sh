#!/usr/bin/env bash

PORT_TEXT=5006
PORT_AUDIO=5007

echo "=========================================="
echo "    تشغيل المساعد الصوتي لـ Pico 2 W"
echo "=========================================="

# تفعيل بيئة بايثون بالمسار المطلق (أهم خطوة!)
source /home/navi/chatboot/venv/bin/activate

# 1. فتح المنفذين فقط مؤقتاً داخل الجدار الناري
echo "[+] فتح المنفذين $PORT_TEXT و $PORT_AUDIO في الجدار الناري مؤقتاً..."
sudo iptables -I INPUT -p udp --dport $PORT_TEXT -j ACCEPT 2>/dev/null
sudo iptables -I INPUT -p udp --dport $PORT_AUDIO -j ACCEPT 2>/dev/null

# دالة التنظيف وإعادة غلق المنافذ عند الخروج (Ctrl+C)
cleanup() {
    echo ""
    echo "[*] جاري إيقاف البرامج وإعادة تأمين الجهاز..."
    
    # إيقاف برنامج الاستقبال إذا كان يعمل
    if [ -n "$REC_PID" ] && kill -0 "$REC_PID" 2>/dev/null; then
        kill "$REC_PID" 2>/dev/null
    fi

    # حذف القواعد وإعادة قفل المنفذين فوراً لحماية جهازك
    echo "[-] إغلاق المنافذ واستعادة حماية الجدار الناري..."
    sudo iptables -D INPUT -p udp --dport $PORT_TEXT -j ACCEPT 2>/dev/null
    sudo iptables -D INPUT -p udp --dport $PORT_AUDIO -j ACCEPT 2>/dev/null

    echo "[✓] تم إيقاف كل شيء والجهاز محمي تماماً الآن."
    exit 0
}

# تفعيل التنظيف التلقائي عند الضغط على Ctrl+C أو إغلاق الطرفية
trap cleanup SIGINT SIGTERM EXIT

# 2. تشغيل برنامج الاستقبال (البوت والصوت) في الخلفية
echo "[+] تشغيل مستقبل الصوت والنصوص من Pico..."
python /home/navi/chatboot/pc_receiver.py &
REC_PID=$!

sleep 1

# 3. تشغيل المايك في الواجهة لإرسال صوتك للـ Pico
echo "[+] تشغيل الميكروفون الموجه للـ Pico..."
echo ">>> تحدث الآن في المايك. اضغط Ctrl+C في أي وقت للإيقاف <<<"
python /home/navi/chatboot/listen.py

#!/usr/bin/env bash

echo "=========================================="
echo "    تشغيل المساعد الصوتي لـ Pico 2 W"
echo "=========================================="

# 1. إغلاق أي نسخ قديمة تعمل في الخلفية
echo "[+] إغلاق أي عمليات قديمة..."
pkill -f pc_receiver.py 2>/dev/null
pkill -f listen.py 2>/dev/null
sleep 1

# 2. مسح ملف الكتم إذا كان عالقاً
rm -f /home/navi/chatboot/mute_mic

# 3. إيقاف الجدار الناري نهائياً لضمان وصول الحزم
echo "[+] إيقاف الجدار الناري مؤقتاً..."
sudo systemctl stop firewalld 2>/dev/null
sudo iptables -F 2>/dev/null

# 4. تفعيل بيئة بايثون
source /home/navi/chatboot/venv/bin/activate

# 5. تشغيل مستقبل الصوت في الخلفية
echo "[+] تشغيل مستقبل الصوت والنصوص..."
python /home/navi/chatboot/pc_receiver.py &
REC_PID=$!

# 6. دالة التنظيف عند الخروج (Ctrl+C)
cleanup() {
    echo ""
    echo "[*] جاري إيقاف كل شيء..."
    kill "$REC_PID" 2>/dev/null
    exit 0
}
trap cleanup SIGINT SIGTERM EXIT

sleep 1

# 7. تشغيل المايك في المقدمة
echo "[+] تشغيل الميكروفون..."
echo ">>> تحدث الآن في المايك. اضغط Ctrl+C في أي وقت للإيقاف <<<"
python /home/navi/chatboot/listen.py

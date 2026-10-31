.PHONY: mic bot run

# مسار بايثون داخل البيئة الافتراضية مباشرة (دون الحاجة لعمل activate)
VENV_PYTHON = ~/chatboot/venv/bin/python

mic:
	fish -c "cd ~/chatboot; $(VENV_PYTHON) listen.py"

bot:
	fish -c "cd ~/chatboot; $(VENV_PYTHON) pc_receiver.py"

# الأمر الشامل: يفتح المنافذ في الجدار، يشغل البوت والمايك، ويقفل المنافذ فور الضغط على Ctrl+C
run:
	@echo "=== [1/4] فتح المنفذين 5006 و 5007 مؤقتاً في الجدار الناري ==="
	@sudo iptables -I INPUT -p udp --dport 5006 -j ACCEPT 2>/dev/null || true
	@sudo iptables -I INPUT -p udp --dport 5007 -j ACCEPT 2>/dev/null || true
	@trap 'echo ""; echo "=== [4/4] إغلاق المنافذ وتأمين الجدار الناري..."; \
	       sudo iptables -D INPUT -p udp --dport 5006 -j ACCEPT 2>/dev/null || true; \
	       sudo iptables -D INPUT -p udp --dport 5007 -j ACCEPT 2>/dev/null || true; \
	       kill 0' INT TERM EXIT; \
	echo "=== [2/4] تشغيل مستمع البوت في الخلفية ==="; \
	$(VENV_PYTHON) ~/chatboot/pc_receiver.py & \
	sleep 1; \
	echo "=== [3/4] تشغيل المايك (تحدث الآن! واضغط Ctrl+C للإيقاف) ==="; \
	$(VENV_PYTHON) ~/chatboot/listen.py

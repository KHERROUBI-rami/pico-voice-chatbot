// Sentence recognizer on Pico 2 W
// PC mic -> UDP (float32) -> ring buffer -> Low-pass Filter -> Quantization -> MFCC -> TFLM model

#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <math.h>

#include "pico/stdlib.h"
#include "pico/cyw43_arch.h"
#include "lwip/udp.h"
#include "lwip/pbuf.h"
#include "lwip/netif.h"

#include "audio_data.h"
#include "fft.h"
#include "mfcc.h"
#include "kws.h"
#include "wifi_config.h"

#define UDP_PORT     5005          // audio from the PC microphone comes in here (float32)
#define EVENT_PORT   5006          // recognized text goes to the PC here
#define AUDIO_PORT   5007          // audio answer files go to the PC here
#ifndef PC_IP
#define PC_IP        "172.16.173.56"
#endif

#define HOP_SIZE     (FFT_SIZE / 2)
#define NUM_FRAMES   KWS_FRAMES
#define NUM_BINS     (FFT_SIZE / 2 + 1)

#define RING_SIZE    32768
#define RING_MASK    (RING_SIZE - 1)

// ---- detection settings ----
#define INFER_EVERY    8
#define CMD_THRESHOLD  0.80f
#define CONFIRM_COUNT  2
#define COOLDOWN_MS    2500

// ---- Filter Coefficients (Butterworth Low-pass, Order 5, 7500 Hz) ----
const float B_COEFFS[6] = {0.72736049f, 3.63680246f, 7.27360493f, 7.27360493f, 3.63680246f, 0.72736049f};
const float A_COEFFS[6] = {1.0f, 4.36489385f, 7.65660433f, 6.74371289f, 2.98127143f, 0.52905328f};

// ---- classes ----
static const char *CLASS_NAMES[KWS_NUM_LABELS] = {
    "unknown",
    "hello how are you",
    "tell me about yourself",
    "what is your name",
    "blink the LED",
    "turn on the LED",
    "turn off the LED"
};

// ---- audio ring buffer (Now stores float32) ----
static float ring[RING_SIZE];
static volatile uint32_t head = 0;
static volatile uint32_t tail = 0;
static volatile uint32_t overruns = 0;
static volatile uint32_t udp_packets = 0;

// ---- processing buffers ----
static int8_t frame[FFT_SIZE];
static float  power[NUM_BINS];
static float  mfcc_ring[NUM_FRAMES][NUM_MFCC];
static float  window_buf[NUM_FRAMES][NUM_MFCC];

// ---- LED ----
static bool     led_state = false;
static bool     blinking = false;
static int      blink_toggles_left = 0;
static uint32_t next_toggle_ms = 0;

// ---- UDP socket ----
static struct udp_pcb *event_pcb = NULL;
static err_t last_send_err = ERR_OK;

static void led_set(bool on) {
    led_state = on;
    cyw43_arch_gpio_put(CYW43_WL_GPIO_LED_PIN, on);
}

static void led_update(uint32_t now) {
    if (!blinking) return;
    if ((int32_t)(now - next_toggle_ms) < 0) return;
    led_set(!led_state);
    next_toggle_ms = now + 250;
    if (--blink_toggles_left <= 0) {
        blinking = false;
        led_set(false);
    }
}

// ---- Low-pass Filter (IIR Direct Form I) ----
static float filter_sample(float x) {
    static float x_hist[5] = {0};
    static float y_hist[5] = {0};

    float y = B_COEFFS[0] * x +
              B_COEFFS[1] * x_hist[0] + B_COEFFS[2] * x_hist[1] + 
              B_COEFFS[3] * x_hist[2] + B_COEFFS[4] * x_hist[3] + B_COEFFS[5] * x_hist[4]
            - A_COEFFS[1] * y_hist[0] - A_COEFFS[2] * y_hist[1] - 
              A_COEFFS[3] * y_hist[2] - A_COEFFS[4] * y_hist[3] - A_COEFFS[5] * y_hist[4];

    for (int i = 4; i > 0; i--) {
        x_hist[i] = x_hist[i-1];
        y_hist[i] = y_hist[i-1];
    }
    x_hist[0] = x;
    y_hist[0] = y;
    return y;
}

// ---- Send UDP to PC ----
static bool udp_send_to_pc(const uint8_t *data, size_t len, u16_t port) {
    if (event_pcb == NULL) return false;

    ip_addr_t dst;
    if (!ipaddr_aton(PC_IP, &dst)) return false;

    bool ok = false;
    for (int attempt = 0; attempt < 3 && !ok; attempt++) {
        cyw43_arch_lwip_begin();
        struct pbuf *p = pbuf_alloc(PBUF_TRANSPORT, (u16_t)len, PBUF_RAM);
        if (p != NULL) {
            memcpy(p->payload, data, len);
            err_t e = udp_sendto(event_pcb, p, &dst, port);
            pbuf_free(p);
            if (e == ERR_OK) ok = true;
            else last_send_err = e;
        } else {
            last_send_err = ERR_MEM;
        }
        cyw43_arch_lwip_end();

        if (!ok) sleep_ms(5);
    }
    return ok;
}

static void send_event_to_pc(const char *text) {
    last_send_err = ERR_OK;
    bool ok = udp_send_to_pc((const uint8_t *)text, strlen(text), EVENT_PORT);
    printf("DEBUG: text to PC -> %s : %s (lwIP err %d)\n",
           text, ok ? "sent" : "FAILED", (int)last_send_err);
}

static void send_audio_to_pc(const char *file_id, const unsigned char *audio_data, unsigned int audio_len) {
    printf("DEBUG: Sending audio %s, size %u bytes\n", file_id, audio_len);

    static uint8_t pkt[64 + 512];
    unsigned int total_packets = (audio_len + 511) / 512;
    unsigned int ok_count = 0, fail_count = 0;
    last_send_err = ERR_OK;

    for (unsigned int seq = 0; seq < total_packets; seq++) {
        int header_len = snprintf((char *)pkt, 64, "FILE:%s:%u:%u:", file_id, seq, total_packets);
        unsigned int offset = seq * 512;
        unsigned int payload_len = audio_len - offset;
        if (payload_len > 512) payload_len = 512;
        memcpy(pkt + header_len, audio_data + offset, payload_len);

        if (udp_send_to_pc(pkt, (size_t)header_len + payload_len, AUDIO_PORT)) ok_count++;
        else fail_count++;

        sleep_ms(5);
    }

    printf("DEBUG: audio %s done: %u of %u packets accepted, %u failed\n",
           file_id, ok_count, total_packets, fail_count);
}

static void run_action(int label, uint32_t now) {
    send_event_to_pc(CLASS_NAMES[label]);

    switch (label) {
        case 1: send_audio_to_pc("v1", audio_v1, audio_v1_len); break;
        case 2: send_audio_to_pc("v4", audio_v4, audio_v4_len); break;
        case 3: send_audio_to_pc("v7", audio_v7, audio_v7_len); break;
        case 4:
            printf("ACTION: blinking the LED for 5 seconds\n");
            blinking = true; blink_toggles_left = 20; next_toggle_ms = now; break;
        case 5:
            printf("ACTION: LED on\n"); blinking = false; led_set(true); break;
        case 6:
            printf("ACTION: LED off\n"); blinking = false; led_set(false); break;
        default: break;
    }
}

static void fail(const char *msg) {
    while (true) {
        printf("ERROR: %s\n", msg);
        sleep_ms(2000);
    }
}

// ---- Receive UDP Audio (Now float32) ----
static void on_udp_packet_received(void *arg, struct udp_pcb *pcb, struct pbuf *p,
                                   const ip_addr_t *addr, u16_t port) {
    if (p == NULL) return;
    uint32_t h = head;
    bool full = false;
    udp_packets = udp_packets + 1;
    
    for (struct pbuf *q = p; q != NULL && !full; q = q->next) {
        const float *src = (const float *)q->payload; // Cast to float
        for (u16_t i = 0; i < q->len / sizeof(float); i++) {
            if ((uint32_t)(h - tail) >= RING_SIZE) {
                overruns = overruns + 1;
                full = true;
                break;
            }
            ring[h & RING_MASK] = src[i];
            h++;
        }
    }
    head = h;
    pbuf_free(p);
}

int main() {
    stdio_init_all();
    sleep_ms(2000);
    printf("\nStarting sentence recognizer...\n");

    fft_init();
    mfcc_init();

    if (!kws_init()) fail("model initialization failed");
    if (cyw43_arch_init()) fail("Wi-Fi initialization failed");
    cyw43_arch_enable_sta_mode();
    led_set(false);

    printf("Connecting to Wi-Fi...\n");
    if (cyw43_arch_wifi_connect_timeout_ms(WIFI_SSID, WIFI_PASS, CYW43_AUTH_WPA2_AES_PSK, 15000)) {
        fail("Wi-Fi connection failed (check SSID / password / 2.4 GHz)");
    }
    printf("Wi-Fi connected. Pico IP: %s\n", ip4addr_ntoa(netif_ip4_addr(netif_default)));

    cyw43_arch_lwip_begin();
    struct udp_pcb *pcb = udp_new();
    if (pcb == NULL) { cyw43_arch_lwip_end(); fail("could not create UDP socket"); }
    err_t res = udp_bind(pcb, IP_ANY_TYPE, UDP_PORT);
    if (res != ERR_OK) { cyw43_arch_lwip_end(); fail("UDP bind failed"); }
    udp_recv(pcb, on_udp_packet_received, NULL);

    event_pcb = udp_new();
    if (event_pcb == NULL) { cyw43_arch_lwip_end(); fail("could not create event UDP socket"); }
    cyw43_arch_lwip_end();

    printf("Listening for UDP float32 audio on port %d\n", UDP_PORT);
    printf("Sending recognized text to %s:%d\n", PC_IP, EVENT_PORT);
    printf("Sending audio packets to %s:%d\n", PC_IP, AUDIO_PORT);

    int      wr = 0;
    uint32_t frames_total = 0;
    uint32_t since_infer = 0;
    int      last_label = -1;
    int      streak = 0;
    uint32_t last_trigger_ms = 0;
    uint32_t last_overruns = 0;
    uint32_t last_infer_us = 0;
    uint32_t last_stat_ms = to_ms_since_boot(get_absolute_time());

    while (true) {
        uint32_t now = to_ms_since_boot(get_absolute_time());
        led_update(now);

        while ((uint32_t)(head - tail) >= FFT_SIZE) {
            uint32_t t = tail;
            for (int i = 0; i < FFT_SIZE; i++) {
                // 1. Read raw float32 from ring
                float raw = ring[(t + i) & RING_MASK];
                
                // 2. Apply Low-pass filter
                float filtered = filter_sample(raw);
                
                // 3. Quantize to int8
                float clipped = filtered;
                if (clipped > 1.0f) clipped = 1.0f;
                if (clipped < -1.0f) clipped = -1.0f;
                frame[i] = (int8_t)roundf(clipped * 127.0f);
            }

            process_audio_frame(frame, power);
            compute_mfcc(power, mfcc_ring[wr]);
            wr = (wr + 1) % NUM_FRAMES;
            frames_total++;
            since_infer++;
            tail = t + HOP_SIZE;

            if (frames_total >= NUM_FRAMES && since_infer >= INFER_EVERY) {
                since_infer = 0;
                for (int i = 0; i < NUM_FRAMES; i++) {
                    memcpy(window_buf[i], mfcc_ring[(wr + i) % NUM_FRAMES], sizeof(window_buf[i]));
                }

                float probs[KWS_NUM_LABELS];
                uint32_t t0 = time_us_32();
                int label = kws_run(&window_buf[0][0], probs);
                last_infer_us = time_us_32() - t0;

                if (label >= 0) {
                    float score = probs[label];
                    bool confident = (label != 0) && (score >= CMD_THRESHOLD);

                    if (confident) {
                        if (label == last_label) streak++;
                        else { last_label = label; streak = 1; }
                    } else {
                        last_label = -1;
                        streak = 0;
                    }

                    if (label != 0 && score > 0.5f) {
                        printf("class %d (%s)  score %.2f  streak %d\n",
                               label, CLASS_NAMES[label], score, streak);
                    }

                    now = to_ms_since_boot(get_absolute_time());
                    if (streak >= CONFIRM_COUNT && (now - last_trigger_ms) > COOLDOWN_MS) {
                        last_trigger_ms = now;
                        printf(">>> RECOGNIZED: \"%s\" (%.2f)\n", CLASS_NAMES[label], score);
                        run_action(label, now);
                        streak = 0;
                        last_label = -1;
                    }
                }
            }
        }

        if (overruns != last_overruns) {
            last_overruns = overruns;
            printf("WARNING: ring buffer overrun count: %lu\n", (unsigned long)last_overruns);
        }

        now = to_ms_since_boot(get_absolute_time());
        if (now - last_stat_ms >= 5000) {
            last_stat_ms = now;
            printf("[status] UDP packets: %lu, last inference: %lu us\n",
                   (unsigned long)udp_packets, (unsigned long)last_infer_us);
        }
        sleep_ms(1);
    }
}

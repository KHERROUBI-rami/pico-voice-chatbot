#pragma once
#include <stdint.h>
#include <math.h>

#define FFT_SIZE 512                 // must be a power of 2
#define PI_F     3.14159265358979f

typedef struct {
    float real;
    float imag;
} Complex;

static float   twiddle_cos[FFT_SIZE / 2];
static float   twiddle_sin[FFT_SIZE / 2];
static float   hamming_win[FFT_SIZE];
static Complex fft_buf[FFT_SIZE];    // static: keeps it off the stack

// Call once at startup
static void fft_init(void) {
    for (int i = 0; i < FFT_SIZE / 2; i++) {
        float angle = -2.0f * PI_F * i / FFT_SIZE;
        twiddle_cos[i] = cosf(angle);
        twiddle_sin[i] = sinf(angle);
    }
    for (int i = 0; i < FFT_SIZE; i++) {
        hamming_win[i] = 0.54f - 0.46f * cosf(2.0f * PI_F * i / (FFT_SIZE - 1));
    }
}

// In-place iterative radix-2 FFT (n must equal FFT_SIZE)
static void compute_fft(Complex *x, int n) {
    // Bit-reversal reordering
    for (int i = 1, j = 0; i < n; i++) {
        int bit = n >> 1;
        for (; j & bit; bit >>= 1) j ^= bit;
        j ^= bit;
        if (i < j) {
            Complex tmp = x[i];
            x[i] = x[j];
            x[j] = tmp;
        }
    }

    // Butterflies
    for (int len = 2; len <= n; len <<= 1) {
        int half = len >> 1;
        int step = FFT_SIZE / len;
        for (int i = 0; i < n; i += len) {
            for (int k = 0; k < half; k++) {
                float wr = twiddle_cos[k * step];
                float wi = twiddle_sin[k * step];

                Complex *a = &x[i + k];
                Complex *b = &x[i + k + half];

                float tr = wr * b->real - wi * b->imag;
                float ti = wr * b->imag + wi * b->real;

                b->real = a->real - tr;
                b->imag = a->imag - ti;
                a->real += tr;
                a->imag += ti;
            }
        }
    }
}

// pcm_buffer: FFT_SIZE signed 8-bit samples (exactly as sent by listen.py)
// power_out : array of (FFT_SIZE/2 + 1) floats
static void process_audio_frame(const int8_t *pcm_buffer, float *power_out) {
    for (int i = 0; i < FFT_SIZE; i++) {
        fft_buf[i].real = ((float)pcm_buffer[i] / 128.0f) * hamming_win[i];
        fft_buf[i].imag = 0.0f;
    }

    compute_fft(fft_buf, FFT_SIZE);

    for (int k = 0; k <= FFT_SIZE / 2; k++) {
        power_out[k] = fft_buf[k].real * fft_buf[k].real +
                       fft_buf[k].imag * fft_buf[k].imag;
    }
}

#pragma once
#include <stdint.h>
#include <math.h>
#include "fft.h"

#define SAMPLE_RATE   16000
#define NUM_MEL       26      // عدد مرشحات Mel
#define NUM_MFCC      13      // عدد المعاملات المحتفظ بها
#define MEL_LOW_HZ    80.0f
#define MEL_HIGH_HZ   7600.0f

static int   mel_edges[NUM_MEL + 2];            // رقم الـ bin لكل حافة مرشح
static float dct_table[NUM_MFCC][NUM_MEL];

static float hz_to_mel(float hz)  { return 2595.0f * log10f(1.0f + hz / 700.0f); }
static float mel_to_hz(float mel) { return 700.0f * (powf(10.0f, mel / 2595.0f) - 1.0f); }

// تُستدعى مرة واحدة عند البدء (بعد fft_init)
static void mfcc_init(void) {
    float mel_lo = hz_to_mel(MEL_LOW_HZ);
    float mel_hi = hz_to_mel(MEL_HIGH_HZ);

    // NUM_MEL مثلث يحتاج NUM_MEL + 2 نقطة حافة، موزعة بالتساوي على مقياس Mel
    for (int i = 0; i < NUM_MEL + 2; i++) {
        float mel = mel_lo + (mel_hi - mel_lo) * i / (NUM_MEL + 1);
        float hz  = mel_to_hz(mel);
        int bin   = (int)floorf((FFT_SIZE + 1) * hz / SAMPLE_RATE);
        if (bin > FFT_SIZE / 2) bin = FFT_SIZE / 2;
        mel_edges[i] = bin;
    }

    // جدول DCT-II (بتطبيع orthonormal)
    for (int i = 0; i < NUM_MFCC; i++) {
        float scale = (i == 0) ? sqrtf(1.0f / NUM_MEL) : sqrtf(2.0f / NUM_MEL);
        for (int j = 0; j < NUM_MEL; j++) {
            dct_table[i][j] = scale * cosf(PI_F * i * (j + 0.5f) / NUM_MEL);
        }
    }
}

// power_in : عدد FFT_SIZE/2 + 1 قيمة float قادمة من process_audio_frame()
// mfcc_out : عدد NUM_MFCC قيمة float
static void compute_mfcc(const float *power_in, float *mfcc_out) {
    float log_mel[NUM_MEL];

    // 1. مرشحات Mel المثلثية + اللوغاريتم
    for (int m = 0; m < NUM_MEL; m++) {
        int left = mel_edges[m], center = mel_edges[m + 1], right = mel_edges[m + 2];
        float energy = 0.0f;

        for (int k = left; k < center; k++)               // الجانب الصاعد
            energy += power_in[k] * (float)(k - left) / (float)(center - left);

        for (int k = center; k < right; k++)              // الجانب الهابط
            energy += power_in[k] * (float)(right - k) / (float)(right - center);

        log_mel[m] = logf(energy + 1e-10f);               // لتجنب log(0)
    }

    // 2. الـ DCT للحصول على أول NUM_MFCC معامل
    for (int i = 0; i < NUM_MFCC; i++) {
        float sum = 0.0f;
        for (int j = 0; j < NUM_MEL; j++) sum += log_mel[j] * dct_table[i][j];
        mfcc_out[i] = sum;
    }
}

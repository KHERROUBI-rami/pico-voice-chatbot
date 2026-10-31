#pragma once
// TensorFlow Lite Micro wrapper for the sentence model (7 classes, 2 s window)
#include <stdio.h>
#include <string.h>
#include <math.h>
#include <stdint.h>
#include "pico/stdlib.h"

#include "tensorflow/lite/micro/micro_mutable_op_resolver.h"
#include "tensorflow/lite/micro/micro_interpreter.h"
#include "tensorflow/lite/schema/schema_generated.h"

#include "model.h"      // g_model_data (from train_sentences.py)

// ---- must match train_sentences.py ----
#define KWS_FRAMES      124      // 2 seconds of MFCC frames
#define KWS_COEFFS      13
#define KWS_NUM_LABELS  7        // 0 unknown, 1 hello, 2 about, 3 name, 4 blink, 5 on, 6 off
#define FEAT_MEAN       -1.313614f
#define FEAT_STD        12.117661f

#define KWS_DEBUG       0        // 1 = print all class probabilities on every inference

constexpr int kTensorArenaSize = 96 * 1024;     // check "Arena used" in the log, then reduce
alignas(16) static uint8_t tensor_arena[kTensorArenaSize];

static const tflite::Model*      kws_model   = nullptr;
static tflite::MicroInterpreter* interpreter = nullptr;
static TfLiteTensor*             input       = nullptr;
static TfLiteTensor*             output      = nullptr;

static bool kws_init() {
    kws_model = tflite::GetModel(g_model_data);
    if (kws_model->version() != TFLITE_SCHEMA_VERSION) {
        printf("ERROR: model schema version mismatch (%lu)\n",
               (unsigned long)kws_model->version());
        return false;
    }

    // If the log says "Didn't find op for builtin opcode 'X'", add AddX() here
    // and increase the template number.
    static tflite::MicroMutableOpResolver<10> resolver;
    resolver.AddConv2D();
    resolver.AddDepthwiseConv2D();
    resolver.AddFullyConnected();
    resolver.AddAveragePool2D();
    resolver.AddMaxPool2D();
    resolver.AddReshape();
    resolver.AddSoftmax();
    resolver.AddShape();
    resolver.AddStridedSlice();
    resolver.AddPack();

    static tflite::MicroInterpreter static_interpreter(
        kws_model, resolver, tensor_arena, kTensorArenaSize);
    interpreter = &static_interpreter;

    if (interpreter->AllocateTensors() != kTfLiteOk) {
        printf("ERROR: AllocateTensors failed (missing op in the log above, or arena too small)\n");
        return false;
    }

    input  = interpreter->input(0);
    output = interpreter->output(0);

    int in_elems = 1;
    for (int i = 0; i < input->dims->size; i++) in_elems *= input->dims->data[i];
    int out_elems = 1;
    for (int i = 0; i < output->dims->size; i++) out_elems *= output->dims->data[i];

    if (in_elems != KWS_FRAMES * KWS_COEFFS) {
        printf("ERROR: model input has %d values, code sends %d\n",
               in_elems, KWS_FRAMES * KWS_COEFFS);
        return false;
    }
    if (out_elems != KWS_NUM_LABELS) {
        printf("ERROR: model has %d outputs, code expects %d\n", out_elems, KWS_NUM_LABELS);
        return false;
    }

    printf("Model loaded. Arena used: %u bytes (of %d). Input type %d, output type %d\n",
           (unsigned)interpreter->arena_used_bytes(), kTensorArenaSize,
           (int)input->type, (int)output->type);
    return true;
}

// mfcc  : KWS_FRAMES x KWS_COEFFS floats, frame-major (oldest frame first)
// probs : KWS_NUM_LABELS floats (output)
// returns the index of the most probable class, or -1 on failure
static int kws_run(const float *mfcc, float *probs) {
    const int n = KWS_FRAMES * KWS_COEFFS;

    if (input->type == kTfLiteFloat32) {
        for (int i = 0; i < n; i++)
            input->data.f[i] = (mfcc[i] - FEAT_MEAN) / FEAT_STD;
    } else if (input->type == kTfLiteInt8) {
        const float scale = input->params.scale;
        const int   zp    = input->params.zero_point;
        for (int i = 0; i < n; i++) {
            float x = (mfcc[i] - FEAT_MEAN) / FEAT_STD;
            int q = (int)roundf(x / scale) + zp;
            if (q < -128) q = -128;
            if (q >  127) q =  127;
            input->data.int8[i] = (int8_t)q;
        }
    } else {
        printf("ERROR: unsupported input type\n");
        return -1;
    }

    if (interpreter->Invoke() != kTfLiteOk) {
        printf("ERROR: Invoke failed\n");
        return -1;
    }

    for (int i = 0; i < KWS_NUM_LABELS; i++) {
        if (output->type == kTfLiteFloat32) {
            probs[i] = output->data.f[i];
        } else {
            probs[i] = (output->data.int8[i] - output->params.zero_point) * output->params.scale;
        }
    }

    int best = 0;
    for (int i = 1; i < KWS_NUM_LABELS; i++)
        if (probs[i] > probs[best]) best = i;

#if KWS_DEBUG
    printf("probs:");
    for (int i = 0; i < KWS_NUM_LABELS; i++) printf(" %.2f", probs[i]);
    printf("\n");
#endif
    return best;
}

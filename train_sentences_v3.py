"""
Train the SENTENCE model (7 classes, 2-second window) for the Pico.

Inputs : my_data/<id>/*.wav   your recordings (from record_samples.py)
         Speech Commands      downloaded automatically, used for the "unknown" class
Outputs: model.h, model.tflite, and the numbers to paste into kws.h

Features are computed exactly like fft.h + mfcc.h on the Pico
(16 kHz, FFT 512, hop 256, Hamming, 26 Mel filters, 13 MFCC).
"""
import os, glob, random
import numpy as np
import tensorflow as tf
from scipy.io import wavfile
from scipy.signal import butter, lfilter

# ---------------- settings ----------------
LABELS = ["unknown", "hello", "about", "name", "blink", "on", "off"]   # class 0..6
MY_DIR = "my_data"
EXCLUDE_WORDS = {"on", "off"}            # single words that sound like our commands
AUG_PER_CLIP = 6
N_UNKNOWN_WORDS = {"train": 2000, "val": 200, "test": 200}
N_SILENCE = {"train": 400, "val": 60, "test": 60}
EPOCHS, BATCH = 40, 32

# ---------------- must equal the C code ----------------
FS, FFT_SIZE, HOP = 16000, 512, 256
NUM_MEL, NUM_MFCC = 26, 13
MEL_LO, MEL_HI = 80.0, 7600.0
CUTOFF = 7500.0
WIN = 2 * FS                                   # 2-second window
NUM_FRAMES = (WIN - FFT_SIZE) // HOP + 1       # 124 frames

def hz2mel(h): return 2595.0 * np.log10(1.0 + h / 700.0)
def mel2hz(m): return 700.0 * (10 ** (m / 2595.0) - 1.0)

edges = []
for i in range(NUM_MEL + 2):
    mel = hz2mel(MEL_LO) + (hz2mel(MEL_HI) - hz2mel(MEL_LO)) * i / (NUM_MEL + 1)
    edges.append(min(int(np.floor((FFT_SIZE + 1) * mel2hz(mel) / FS)), FFT_SIZE // 2))
FB = np.zeros((NUM_MEL, FFT_SIZE // 2 + 1), np.float32)
for m in range(NUM_MEL):
    l, c, r = edges[m], edges[m + 1], edges[m + 2]
    for k in range(l, c): FB[m, k] = (k - l) / (c - l)
    for k in range(c, r): FB[m, k] = (r - k) / (r - c)

DCT = np.zeros((NUM_MFCC, NUM_MEL), np.float32)
for i in range(NUM_MFCC):
    s = np.sqrt((1.0 if i == 0 else 2.0) / NUM_MEL)
    for j in range(NUM_MEL):
        DCT[i, j] = s * np.cos(np.pi * i * (j + 0.5) / NUM_MEL)

HAMMING = (0.54 - 0.46 * np.cos(2 * np.pi * np.arange(FFT_SIZE) / (FFT_SIZE - 1))).astype(np.float32)
B, A = butter(5, CUTOFF / (0.5 * FS), btype="low")

def features(waves, chunk=200):
    """waves: (N, WIN) float in [-1,1] -> (N, NUM_FRAMES, 13), as the Pico computes."""
    out = []
    for s in range(0, len(waves), chunk):
        x = lfilter(B, A, waves[s:s + chunk], axis=1)            # same low-pass as listen.py
        x = np.rint(np.clip(x, -1, 1) * 127) / 128.0              # int8 quantize, C divides by 128
        fr = np.lib.stride_tricks.sliding_window_view(x, FFT_SIZE, axis=1)[:, ::HOP][:, :NUM_FRAMES]
        spec = np.fft.rfft(fr * HAMMING, axis=2)
        power = (spec.real ** 2 + spec.imag ** 2).astype(np.float32)
        logmel = np.log(power @ FB.T + 1e-10)
        out.append((logmel @ DCT.T).astype(np.float32))
    return np.concatenate(out)

# ---------------- helpers ----------------
def load_wav(path):
    sr, w = wavfile.read(path)
    w = w.astype(np.float32) / (32768.0 if w.dtype == np.int16 else 1.0)
    if w.ndim > 1: w = w[:, 0]
    return w

def crop(w, offset):
    out = np.zeros(WIN, np.float32)
    seg = w[offset:offset + WIN]
    out[:len(seg)] = seg
    return out

def shift(w, s):
    out = np.zeros_like(w)
    if s > 0: out[s:] = w[:-s]
    elif s < 0: out[:s] = w[-s:]
    else: out[:] = w
    return out

def augment(w, noises):
    w = shift(w, random.randint(-4800, 4800))            # +-0.3 s
    w = w * random.uniform(0.4, 1.6)                      # volume changes
    n = random.choice(noises)
    s = random.randint(0, len(n) - WIN)
    w = w + n[s:s + WIN] * random.uniform(0, 0.1)         # background noise
    return np.clip(w, -1, 1)

def get_speech_commands():
    p = tf.keras.utils.get_file(
        "speech_commands_v0.02.tar.gz",
        "http://download.tensorflow.org/data/speech_commands_v0.02.tar.gz",
        extract=True, cache_subdir="speech_commands")
    root = os.path.dirname(p) if os.path.isfile(p) else p
    if not os.path.isdir(os.path.join(root, "_background_noise_")):
        sub = os.path.join(root, "speech_commands_v0.02")
        if os.path.isdir(sub): root = sub
    return root

def sc_unknown(files, count):
    """Random 1-2 Speech Commands words placed inside a 2-second window."""
    out = []
    for _ in range(count):
        buf = np.zeros(WIN, np.float32)
        pos = random.randint(0, 6000)
        for _ in range(1 if random.random() < 0.5 else 2):
            w = load_wav(random.choice(files))[:FS]
            end = min(pos + len(w), WIN)
            buf[pos:end] = w[:end - pos]
            pos += len(w) + random.randint(0, 3000)
            if pos >= WIN: break
        out.append(buf)
    return out

# ---------------- main ----------------
def main():
    random.seed(0); np.random.seed(0)
    K = len(LABELS)
    splits = ("train", "val", "test")

    root = get_speech_commands()
    rd = lambda f: set(open(os.path.join(root, f)).read().split())
    val_set, test_set = rd("validation_list.txt"), rd("testing_list.txt")
    noises = [load_wav(f) for f in glob.glob(os.path.join(root, "_background_noise_", "*.wav"))]

    sc_files = {s: [] for s in splits}
    for d in sorted(os.listdir(root)):
        dp = os.path.join(root, d)
        if not os.path.isdir(dp) or d.startswith("_") or d in EXCLUDE_WORDS: continue
        for f in glob.glob(os.path.join(dp, "*.wav")):
            rel = f"{d}/{os.path.basename(f)}"
            sc_files["val" if rel in val_set else "test" if rel in test_set else "train"].append(f)

    X = {s: [] for s in splits}
    Y = {s: [] for s in splits}

    # ---- your recordings ----
    for y, name in enumerate(LABELS):
        files = sorted(glob.glob(os.path.join(MY_DIR, name, "*.wav")))
        if not files:
            print(f"WARNING: no recordings found for '{name}'")
            continue
        random.shuffle(files)
        n = len(files)
        n_test = max(1, round(0.1 * n)); n_val = max(1, round(0.1 * n))
        parts = {"test": files[:n_test], "val": files[n_test:n_test + n_val],
                 "train": files[n_test + n_val:]}
        for s, fl in parts.items():
            for f in fl:
                w = load_wav(f)
                center = max(0, (len(w) - WIN) // 2)
                if s == "train":
                    X[s].append(crop(w, center)); Y[s].append(y)       # one clean copy
                    for _ in range(AUG_PER_CLIP):
                        off = random.randint(0, max(0, len(w) - WIN))
                        X[s].append(augment(crop(w, off), noises)); Y[s].append(y)
                else:
                    X[s].append(crop(w, center)); Y[s].append(y)

    # ---- unknown: Speech Commands words + silence/noise ----
    for s in splits:
        for w in sc_unknown(sc_files[s], N_UNKNOWN_WORDS[s]):
            X[s].append(augment(w, noises) if s == "train" else w); Y[s].append(0)
        for i in range(N_SILENCE[s]):
            n = random.choice(noises)
            st = random.randint(0, len(n) - WIN)
            # one third of the clips are almost silent (very low volume)
            gain = random.uniform(0, 0.02) if i % 3 == 0 else random.uniform(0, 1)
            X[s].append(n[st:st + WIN] * gain); Y[s].append(0)
        for _ in range(max(5, N_SILENCE[s] // 20)):          # exact digital silence
            X[s].append(np.zeros(WIN, np.float32)); Y[s].append(0)

    for s in splits:
        print(s, len(X[s]), "samples; per class:", np.bincount(Y[s], minlength=K).tolist())

    F = {s: features(np.array(X[s], dtype=np.float32)) for s in splits}
    Y = {s: np.array(Y[s]) for s in splits}
    mean, std = float(F["train"].mean()), float(F["train"].std())
    F = {s: ((v - mean) / std)[..., None] for s, v in F.items()}

    # ---------------- model ----------------
    L = tf.keras.layers
    def block(x, ch):
        x = L.DepthwiseConv2D(3, padding="same")(x); x = L.BatchNormalization()(x); x = L.ReLU()(x)
        x = L.Conv2D(ch, 1)(x); x = L.BatchNormalization()(x); return L.ReLU()(x)
    inp = tf.keras.Input((NUM_FRAMES, NUM_MFCC, 1))
    x = L.Conv2D(16, 3, padding="same")(inp); x = L.BatchNormalization()(x); x = L.ReLU()(x)
    x = L.MaxPooling2D(2)(x)                      # 62 x 6
    x = block(x, 32); x = L.MaxPooling2D(2)(x)    # 31 x 3
    x = block(x, 32)
    x = L.AveragePooling2D((8, 3), strides=(8, 3))(x)   # 3 x 1 : keeps coarse time order
    x = L.Flatten()(x)
    x = L.Dense(64, activation="relu")(x); x = L.Dropout(0.3)(x)
    out = L.Dense(K, activation="softmax")(x)
    model = tf.keras.Model(inp, out)
    model.compile("adam", "sparse_categorical_crossentropy", metrics=["accuracy"])

    counts = np.maximum(np.bincount(Y["train"], minlength=K), 1)
    cw = {i: float((len(Y["train"]) / (K * counts[i])) ** 0.5) for i in range(K)}
    model.fit(F["train"], Y["train"], validation_data=(F["val"], Y["val"]),
              epochs=EPOCHS, batch_size=BATCH, class_weight=cw,
              callbacks=[tf.keras.callbacks.EarlyStopping(patience=8, restore_best_weights=True)])

    loss, acc = model.evaluate(F["test"], Y["test"], verbose=0)
    print(f"\nFloat model test accuracy: {acc:.3f}")
    pred = np.argmax(model.predict(F["test"], verbose=0), axis=1)
    print("Confusion matrix (rows = true, columns = predicted):")
    print("labels:", LABELS)
    print(tf.math.confusion_matrix(Y["test"], pred, num_classes=K).numpy())

    # ---------------- int8 quantization ----------------
    def rep():
        for i in np.random.choice(len(F["train"]), min(300, len(F["train"])), replace=False):
            yield [F["train"][i:i + 1].astype(np.float32)]
    conv = tf.lite.TFLiteConverter.from_keras_model(model)
    conv.optimizations = [tf.lite.Optimize.DEFAULT]
    conv.representative_dataset = rep
    conv.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
    conv.inference_input_type = tf.int8
    conv.inference_output_type = tf.int8
    tfl = conv.convert()
    open("model.tflite", "wb").write(tfl)

    # check the int8 model itself (this is what runs on the Pico)
    interp = tf.lite.Interpreter(model_content=tfl); interp.allocate_tensors()
    ind, outd = interp.get_input_details()[0], interp.get_output_details()[0]
    scale, zp = ind["quantization"]
    correct = 0
    for xi, yi in zip(F["test"], Y["test"]):
        q = np.clip(np.round(xi / scale) + zp, -128, 127).astype(np.int8)
        interp.set_tensor(ind["index"], q[None]); interp.invoke()
        correct += int(np.argmax(interp.get_tensor(outd["index"])[0]) == yi)
    print(f"INT8 TFLite test accuracy: {correct / len(Y['test']):.3f}")

    with open("model.h", "w") as f:
        f.write("#pragma once\nalignas(8) const unsigned char g_model_data[] = {\n")
        for i in range(0, len(tfl), 12):
            f.write("  " + ", ".join(f"0x{b:02x}" for b in tfl[i:i + 12]) + ",\n")
        f.write(f"}};\nconst unsigned int g_model_len = {len(tfl)};\n")

    print(f"\nmodel.h written ({len(tfl)} bytes). Numbers for kws.h:")
    print(f"#define KWS_FRAMES      {NUM_FRAMES}")
    print(f"#define KWS_NUM_LABELS  {K}")
    print(f"#define FEAT_MEAN       {mean:.6f}f")
    print(f"#define FEAT_STD        {std:.6f}f")

if __name__ == "__main__":
    main()

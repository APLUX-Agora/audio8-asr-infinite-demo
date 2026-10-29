// SPDX-License-Identifier: Apache-2.0
// Standalone caller of the delivered C ABI, not an inference implementation.
#include "audio8_asr.h"

#include <algorithm>
#include <chrono>
#include <csignal>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <iterator>
#include <memory>
#include <stdexcept>
#include <string>
#include <thread>
#include <vector>

namespace {
volatile std::sig_atomic_t stop_signal = 0;
void request_stop(int sig) { if (!stop_signal) stop_signal = sig; }
void check_stop() { if (stop_signal) throw std::runtime_error("interrupted"); }

uint16_t u16(const std::vector<unsigned char>& b, size_t p) {
    return static_cast<uint16_t>(b.at(p) | (b.at(p + 1) << 8));
}
uint32_t u32(const std::vector<unsigned char>& b, size_t p) {
    return uint32_t(b.at(p)) | (uint32_t(b.at(p + 1)) << 8) |
           (uint32_t(b.at(p + 2)) << 16) | (uint32_t(b.at(p + 3)) << 24);
}
bool tag(const std::vector<unsigned char>& b, size_t p, const char* value) {
    return p <= b.size() && b.size() - p >= 4 && std::equal(value, value + 4, b.begin() + p);
}
std::vector<float> read_wav(const std::string& path) {
    std::ifstream input(path.c_str(), std::ios::binary);
    if (!input) throw std::runtime_error("cannot open WAV: " + path);
    std::vector<unsigned char> b((std::istreambuf_iterator<char>(input)), std::istreambuf_iterator<char>());
    if (b.size() < 12 || !tag(b, 0, "RIFF") || !tag(b, 8, "WAVE"))
        throw std::runtime_error("expected a RIFF/WAVE file");
    const uint64_t end = uint64_t(u32(b, 4)) + 8;
    if (end > b.size() || end < 12) throw std::runtime_error("truncated RIFF file");
    bool format = false, found_data = false;
    size_t data = 0, bytes = 0;
    for (size_t p = 12; p + 8 <= end;) {
        const uint32_t n = u32(b, p + 4);
        const size_t payload = p + 8;
        if (uint64_t(n) > end - payload) throw std::runtime_error("truncated WAV chunk");
        if (tag(b, p, "fmt ")) {
            if (n < 16 || u16(b, payload) != 1 || u16(b, payload + 2) != 1 ||
                u32(b, payload + 4) != 16000 || u32(b, payload + 8) != 32000 ||
                u16(b, payload + 12) != 2 || u16(b, payload + 14) != 16)
                throw std::runtime_error("use 16 kHz mono PCM16 WAV; convert other formats first");
            format = true;
        } else if (tag(b, p, "data")) {
            if (found_data) throw std::runtime_error("multiple WAV data chunks are unsupported");
            found_data = true; data = payload; bytes = n;
        }
        const uint64_t next = uint64_t(payload) + n + (n & 1U);
        if (next > end) throw std::runtime_error("missing WAV chunk padding");
        p = static_cast<size_t>(next);
    }
    if (!format || !found_data || !bytes || bytes % 2)
        throw std::runtime_error("missing format or empty/malformed PCM16 data");
    std::vector<float> pcm(bytes / 2);
    for (size_t i = 0; i < pcm.size(); ++i) {
        const uint16_t raw = u16(b, data + 2 * i);
        const int value = raw >= 32768 ? int(raw) - 65536 : int(raw);
        pcm[i] = value / 32768.0f;
    }
    return pcm;
}
std::string words_json(const std::vector<std::string>& words) {
    static const char hex[] = "0123456789abcdef";
    std::string out = "[";
    for (size_t i = 0; i < words.size(); ++i) {
        if (i) out += ',';
        out += '"';
        for (unsigned char c : words[i]) {
            if (c == '"' || c == '\\') { out += '\\'; out += char(c); }
            else if (c < 32) { out += "\\u00"; out += hex[c >> 4]; out += hex[c & 15]; }
            else out += char(c);
        }
        out += '"';
    }
    return out + ']';
}
int checked(a8_engine* e, int result) {
    if (result < 0) throw std::runtime_error(std::string("SDK error ") + std::to_string(result) + ": " + a8_last_error(e));
    check_stop();
    return result;
}
void drain(a8_engine* e, int count) {
    a8_token tokens[64];
    while (count > 0) {
        const int n = checked(e, a8_read_tokens(e, tokens, 64));
        if (!n) throw std::runtime_error("SDK token queue unexpectedly empty");
        for (int i = 0; i < n; ++i) {
            char small[64];
            int bytes = checked(e, a8_token_bytes(e, tokens[i].id, small, sizeof(small)));
            if (bytes > int(sizeof(small))) {
                std::vector<char> text(static_cast<size_t>(bytes));
                bytes = checked(e, a8_token_bytes(e, tokens[i].id, text.data(), bytes));
                std::cout.write(text.data(), bytes);
            } else std::cout.write(small, bytes);
        }
        std::cout.flush();
        count -= n;
    }
}
}  // namespace

int main(int argc, char** argv) {
    try {
        std::string models, audio, lang = "en", tokenizer;
        std::vector<std::string> words;
        int clock = 160;
        bool realtime = false;
        for (int i = 1; i < argc; ++i) {
            const std::string option = argv[i];
            if (option == "--help") {
                std::cout << "Usage: transcribe_file --models PACKAGE [--clock-ms 160|80] [--lang en|zh] "
                             "[--realtime] [--hotword TERM] [--tokenizer FILE] AUDIO.wav\n";
                return 0;
            }
            if (option == "--realtime") { realtime = true; continue; }
            if (option == "--models" || option == "--clock-ms" || option == "--lang" ||
                option == "--hotword" || option == "--tokenizer") {
                if (++i == argc) throw std::runtime_error("missing value for " + option);
                const std::string value = argv[i];
                if (option == "--models") models = value;
                else if (option == "--clock-ms") {
                    if (value != "160" && value != "80") throw std::runtime_error("clock must be 160 or 80");
                    clock = value == "160" ? 160 : 80;
                } else if (option == "--lang") lang = value;
                else if (option == "--hotword") words.push_back(value);
                else tokenizer = value;
            } else if (!option.empty() && option[0] == '-') throw std::runtime_error("unknown option: " + option);
            else if (audio.empty()) audio = option;
            else throw std::runtime_error("expected one WAV file");
        }
        if (models.empty() || audio.empty() || (lang != "en" && lang != "zh"))
            throw std::runtime_error("use --models PACKAGE --lang en|zh AUDIO.wav; see --help");
        const std::vector<float> pcm = read_wav(audio);
        std::signal(SIGTERM, request_stop);
        std::signal(SIGINT, request_stop);
        a8_options options;
        a8_default_options(&options);
        options.clock_ms = clock;
        options.lang = lang == "en" ? A8_LANG_EN : A8_LANG_ZH;
        // Native creation must return before a pending signal can unwind ownership.
        std::unique_ptr<a8_engine, decltype(&a8_destroy)> engine(a8_create(models.c_str(), &options), a8_destroy);
        if (!engine) throw std::runtime_error(std::string("create failed: ") + a8_create_error());
        check_stop();
        checked(engine.get(), a8_reset(engine.get()));
        if (!words.empty()) {
            checked(engine.get(), a8_set_hotwords(engine.get(), tokenizer.empty() ? nullptr : tokenizer.c_str(), words_json(words).c_str(), 50, 6, 8));
        }
        std::cerr << "[example] engine ready; " << clock << " ms; " << lang << std::endl;
        const auto start = std::chrono::steady_clock::now();
        for (size_t i = 0; i < pcm.size(); i += 1600) {
            check_stop();
            const int n = static_cast<int>(std::min(size_t(1600), pcm.size() - i));
            drain(engine.get(), checked(engine.get(), a8_feed(engine.get(), pcm.data() + i, n)));
            if (realtime) {
                std::this_thread::sleep_until(start + std::chrono::microseconds((i + n) * 1000000ULL / 16000));
                check_stop();
            }
        }
        drain(engine.get(), checked(engine.get(), a8_finish(engine.get(), -1)));
        std::cout << std::endl;
        engine.reset();  // Explicit normal release; exceptions also use this deleter.
        std::cerr << "[example] engine closed" << std::endl;
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "[example] " << error.what() << std::endl;
        return stop_signal ? 128 + stop_signal : 1;
    }
}

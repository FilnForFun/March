"""
QMC/MGG 音乐文件解密脚本
基于 unlock-music (ix64/unlock-music) 算法的 Python 实现
仅供个人已购买版权音乐的本地解密使用
"""
import os
import sys
import math
import struct
from typing import Tuple, Optional

# ============================================================
# TEA Cipher (ported from unlock-music/src/utils/tea.ts)
# ============================================================
class TeaCipher:
    BLOCK_SIZE = 8
    KEY_SIZE = 16
    DELTA = 0x9E3779B9
    NUM_ROUNDS = 64

    def __init__(self, key: bytes, rounds: int = NUM_ROUNDS):
        if len(key) != 16:
            raise ValueError('incorrect key size')
        if rounds % 2 != 0:
            raise ValueError('odd number of rounds')
        self.rounds = rounds
        self.k0 = struct.unpack('>I', key[0:4])[0]
        self.k1 = struct.unpack('>I', key[4:8])[0]
        self.k2 = struct.unpack('>I', key[8:12])[0]
        self.k3 = struct.unpack('>I', key[12:16])[0]

    def decrypt_block(self, data: bytes) -> bytes:
        v0 = struct.unpack('>I', data[0:4])[0]
        v1 = struct.unpack('>I', data[4:8])[0]
        s = (self.DELTA * self.rounds // 2) & 0xFFFFFFFF
        for _ in range(self.rounds // 2):
            v1 = (v1 - (((v0 << 4) + self.k2) ^ (v0 + s) ^ ((v0 >> 5) + self.k3))) & 0xFFFFFFFF
            v0 = (v0 - (((v1 << 4) + self.k0) ^ (v1 + s) ^ ((v1 >> 5) + self.k1))) & 0xFFFFFFFF
            s = (s - self.DELTA) & 0xFFFFFFFF
        return struct.pack('>II', v0, v1)


# ============================================================
# Key Derivation (from unlock-music/src/decrypt/qmc_key.ts)
# ============================================================
def simple_make_key(salt: int, length: int) -> list:
    key_buf = []
    for i in range(length):
        tmp = math.tan(salt + i * 0.1)
        key_buf.append(int(abs(tmp) * 100.0) & 0xFF)
    return key_buf


def decrypt_tencent_tea(in_buf: bytes, key: bytes) -> bytes:
    if len(in_buf) % 8 != 0:
        raise ValueError('inBuf size not a multiple of the block size')
    if len(in_buf) < 16:
        raise ValueError('inBuf size too small')

    blk = TeaCipher(key, 32)
    tmp_buf = blk.decrypt_block(in_buf[0:8])

    n_pad = tmp_buf[0] & 0x7
    out_len = len(in_buf) - 1 - n_pad - 2 - 7

    iv_prev = b'\x00' * 8
    iv_cur = in_buf[0:8]
    in_pos = 8

    tmp_idx = 1 + n_pad

    def crypt_block():
        nonlocal iv_prev, iv_cur, tmp_buf, in_pos, tmp_idx
        iv_prev = iv_cur
        iv_cur = in_buf[in_pos:in_pos + 8]
        xored = bytes([tmp_buf[j] ^ iv_cur[j] for j in range(8)])
        tmp_buf = blk.decrypt_block(xored)
        in_pos += 8
        tmp_idx = 0

    for i in range(1, 3):
        if tmp_idx < 8:
            tmp_idx += 1
        else:
            crypt_block()

    out_buf = bytearray()
    out_pos = 0
    while out_pos < out_len:
        if tmp_idx < 8:
            out_buf.append(tmp_buf[tmp_idx] ^ iv_prev[tmp_idx])
            out_pos += 1
            tmp_idx += 1
        else:
            crypt_block()

    for i in range(1, 8):
        if tmp_buf[tmp_idx] != iv_prev[tmp_idx]:
            raise ValueError('zero check failed')

    return bytes(out_buf)


def qmc_derive_key(raw: bytes) -> bytes:
    import base64
    raw_dec = base64.b64decode(raw)
    n = len(raw_dec)
    if n < 16:
        raise ValueError('key length is too short')

    simple_key = simple_make_key(106, 8)
    tea_key = bytearray(16)
    for i in range(8):
        tea_key[i << 1] = simple_key[i]
        tea_key[(i << 1) + 1] = raw_dec[i]

    sub = decrypt_tencent_tea(raw_dec[8:], bytes(tea_key))
    return raw_dec[:8] + sub


# ============================================================
# Stream Ciphers (from unlock-music/src/decrypt/qmc_cipher.ts)
# ============================================================
class QmcStaticCipher:
    static_cipher_box = bytes([
        0x77, 0x48, 0x32, 0x73, 0xDE, 0xF2, 0xC0, 0xC8,
        0x95, 0xEC, 0x30, 0xB2, 0x51, 0xC3, 0xE1, 0xA0,
        0x9E, 0xE6, 0x9D, 0xCF, 0xFA, 0x7F, 0x14, 0xD1,
        0xCE, 0xB8, 0xDC, 0xC3, 0x4A, 0x67, 0x93, 0xD6,
        0x28, 0xC2, 0x91, 0x70, 0xCA, 0x8D, 0xA2, 0xA4,
        0xF0, 0x08, 0x61, 0x90, 0x7E, 0x6F, 0xA2, 0xE0,
        0xEB, 0xAE, 0x3E, 0xB6, 0x67, 0xC7, 0x92, 0xF4,
        0x91, 0xB5, 0xF6, 0x6C, 0x5E, 0x84, 0x40, 0xF7,
        0xF3, 0x1B, 0x02, 0x7F, 0xD5, 0xAB, 0x41, 0x89,
        0x28, 0xF4, 0x25, 0xCC, 0x52, 0x11, 0xAD, 0x43,
        0x68, 0xA6, 0x41, 0x8B, 0x84, 0xB5, 0xFF, 0x2C,
        0x92, 0x4A, 0x26, 0xD8, 0x47, 0x6A, 0x7C, 0x95,
        0x61, 0xCC, 0xE6, 0xCB, 0xBB, 0x3F, 0x47, 0x58,
        0x89, 0x75, 0xC3, 0x75, 0xA1, 0xD9, 0xAF, 0xCC,
        0x08, 0x73, 0x17, 0xDC, 0xAA, 0x9A, 0xA2, 0x16,
        0x41, 0xD8, 0xA2, 0x06, 0xC6, 0x8B, 0xFC, 0x66,
        0x34, 0x9F, 0xCF, 0x18, 0x23, 0xA0, 0x0A, 0x74,
        0xE7, 0x2B, 0x27, 0x70, 0x92, 0xE9, 0xAF, 0x37,
        0xE6, 0x8C, 0xA7, 0xBC, 0x62, 0x65, 0x9C, 0xC2,
        0x08, 0xC9, 0x88, 0xB3, 0xF3, 0x43, 0xAC, 0x74,
        0x2C, 0x0F, 0xD4, 0xAF, 0xA1, 0xC3, 0x01, 0x64,
        0x95, 0x4E, 0x48, 0x9F, 0xF4, 0x35, 0x78, 0x95,
        0x7A, 0x39, 0xD6, 0x6A, 0xA0, 0x6D, 0x40, 0xE8,
        0x4F, 0xA8, 0xEF, 0x11, 0x1D, 0xF3, 0x1B, 0x3F,
        0x3F, 0x07, 0xDD, 0x6F, 0x5B, 0x19, 0x30, 0x19,
        0xFB, 0xEF, 0x0E, 0x37, 0xF0, 0x0E, 0xCD, 0x16,
        0x49, 0xFE, 0x53, 0x47, 0x13, 0x1A, 0xBD, 0xA4,
        0xF1, 0x40, 0x19, 0x60, 0x0E, 0xED, 0x68, 0x09,
        0x06, 0x5F, 0x4D, 0xCF, 0x3D, 0x1A, 0xFE, 0x20,
        0x77, 0xE4, 0xD9, 0xDA, 0xF9, 0xA4, 0x2B, 0x76,
        0x1C, 0x71, 0xDB, 0x00, 0xBC, 0xFD, 0x0C, 0x6C,
        0xA5, 0x47, 0xF7, 0xF6, 0x00, 0x79, 0x4A, 0x11,
    ])

    @staticmethod
    def get_mask(offset: int) -> int:
        if offset > 0x7FFF:
            offset %= 0x7FFF
        return QmcStaticCipher.static_cipher_box[(offset * offset + 27) & 0xFF]

    def decrypt(self, buf: bytearray, offset: int):
        for i in range(len(buf)):
            buf[i] ^= self.get_mask(offset + i)


class QmcMapCipher:
    def __init__(self, key: bytes):
        if len(key) == 0:
            raise ValueError('invalid key size')
        self.key = key
        self.n = len(key)

    @staticmethod
    def rotate(value: int, bits: int) -> int:
        rotate = (bits + 4) % 8
        left = value << rotate
        right = value >> rotate
        return (left | right) & 0xFF

    def get_mask(self, offset: int) -> int:
        if offset > 0x7FFF:
            offset %= 0x7FFF
        idx = (offset * offset + 71214) % self.n
        return self.rotate(self.key[idx], idx & 0x7)

    def decrypt(self, buf: bytearray, offset: int):
        for i in range(len(buf)):
            buf[i] ^= self.get_mask(offset + i)


class QmcRC4Cipher:
    FIRST_SEGMENT_SIZE = 0x80
    SEGMENT_SIZE = 5120

    def __init__(self, key: bytes):
        if len(key) == 0:
            raise ValueError('invalid key size')
        self.key = key
        self.N = len(key)
        self.S = bytearray(self.N)
        for i in range(self.N):
            self.S[i] = i & 0xFF
        j = 0
        for i in range(self.N):
            j = (self.S[i] + j + self.key[i % self.N]) % self.N
            self.S[i], self.S[j] = self.S[j], self.S[i]

        self.hash = 1
        for i in range(self.N):
            value = self.key[i]
            if not value:
                continue
            next_hash = (self.hash * value) & 0xFFFFFFFF
            if next_hash == 0 or next_hash <= self.hash:
                break
            self.hash = next_hash

    def _get_segment_key(self, id_val: int) -> int:
        seed = self.key[id_val % self.N]
        idx = int((self.hash / ((id_val + 1) * seed)) * 100.0)
        return idx % self.N

    def _enc_first_segment(self, buf: bytearray, offset: int):
        for i in range(len(buf)):
            buf[i] ^= self.key[self._get_segment_key(offset + i)]

    def _enc_a_segment(self, buf: bytearray, offset: int):
        S = self.S[:]
        skip_len = (offset % self.SEGMENT_SIZE) + self._get_segment_key(offset // self.SEGMENT_SIZE)
        j = 0
        k = 0
        for i in range(-skip_len, len(buf)):
            j = (j + 1) % self.N
            k = (S[j] + k) % self.N
            S[k], S[j] = S[j], S[k]
            if i >= 0:
                buf[i] ^= S[(S[j] + S[k]) % self.N]

    def decrypt(self, buf: bytearray, offset: int):
        to_process = len(buf)
        processed = 0

        if offset < self.FIRST_SEGMENT_SIZE:
            seg_len = min(len(buf), self.FIRST_SEGMENT_SIZE - offset)
            self._enc_first_segment(buf[:seg_len], offset)
            to_process -= seg_len
            processed += seg_len
            offset += seg_len
            if to_process == 0:
                return

        if offset % self.SEGMENT_SIZE != 0:
            seg_len = min(self.SEGMENT_SIZE - (offset % self.SEGMENT_SIZE), to_process)
            self._enc_a_segment(buf[processed:processed + seg_len], offset)
            to_process -= seg_len
            processed += seg_len
            offset += seg_len
            if to_process == 0:
                return

        while to_process > self.SEGMENT_SIZE:
            self._enc_a_segment(buf[processed:processed + self.SEGMENT_SIZE], offset)
            to_process -= self.SEGMENT_SIZE
            processed += self.SEGMENT_SIZE
            offset += self.SEGMENT_SIZE

        if to_process > 0:
            self._enc_a_segment(buf[processed:], offset)


# ============================================================
# QmcDecoder (from unlock-music/src/decrypt/qmc.ts)
# ============================================================
class QmcDecoder:
    BYTE_COMMA = ord(',')

    def __init__(self, file_data: bytes):
        self.file = file_data
        self.size = len(file_data)
        self.decoded = False
        self.audio_size = 0
        self.cipher = None
        self.song_id = None
        self._search_key()

    def _search_key(self):
        last4 = self.file[-4:]

        if last4 == b'QTag':
            size_buf = self.file[-8:-4]
            key_size = struct.unpack('>I', size_buf)[0]
            self.audio_size = self.size - key_size - 8

            raw_key = self.file[self.audio_size:self.size - 8]
            key_end = raw_key.find(b',')
            if key_end < 0:
                raise ValueError('invalid key: search raw key failed')
            self._set_cipher(raw_key[:key_end])

            id_buf = raw_key[key_end + 1:]
            id_end = id_buf.find(b',')
            if id_end < 0:
                raise ValueError('invalid key: search song id failed')
            self.song_id = int(id_buf[:id_end].decode('ascii', errors='replace'))
        else:
            key_size = struct.unpack('<I', last4)[0]
            if key_size < 0x300:
                self.audio_size = self.size - key_size - 4
                raw_key = self.file[self.audio_size:self.size - 4]
                self._set_cipher(raw_key)
            else:
                self.audio_size = self.size
                self.cipher = QmcStaticCipher()

    def _set_cipher(self, raw_key: bytes):
        try:
            key_dec = qmc_derive_key(raw_key)
        except Exception:
            key_dec = raw_key

        if len(key_dec) > 300:
            self.cipher = QmcRC4Cipher(key_dec)
        else:
            self.cipher = QmcMapCipher(key_dec)

    def decrypt(self) -> bytes:
        if not self.cipher:
            raise ValueError('no cipher found')
        if not self.audio_size or self.audio_size <= 0:
            raise ValueError('invalid audio size')

        audio_buf = bytearray(self.file[:self.audio_size])
        if not self.decoded:
            self.cipher.decrypt(audio_buf, 0)
            self.decoded = True
        return bytes(audio_buf)


# ============================================================
# Main
# ============================================================
def detect_ext(decrypted: bytes) -> str:
    """Detect audio format from file header"""
    if decrypted[:4] == b'OggS':
        return 'ogg'
    elif decrypted[:4] == b'fLaC':
        return 'flac'
    elif decrypted[:3] == b'ID3' or decrypted[:2] == b'\xff\xfb':
        return 'mp3'
    elif decrypted[:4] == b'\xff\xf1' or decrypted[:4] == b'\xff\xf9':
        return 'aac'
    return 'ogg'  # default for MGG files


def decrypt_file(input_path: str, output_path: str = None) -> bool:
    """Decrypt a single QMC/MGG file"""
    fname = os.path.basename(input_path)
    ext = os.path.splitext(fname)[1].lower().lstrip('.')

    print(f'  [{fname}] ', end='', flush=True)

    try:
        with open(input_path, 'rb') as f:
            data = f.read()

        decoder = QmcDecoder(data)
        decrypted = decoder.decrypt()

        detected_ext = detect_ext(decrypted)
        if output_path is None:
            base = os.path.splitext(input_path)[0]
            output_path = base + '.' + detected_ext

        with open(output_path, 'wb') as f:
            f.write(decrypted)

        size_mb = len(decrypted) / (1024 * 1024)
        print(f'OK -> {detected_ext} ({size_mb:.1f}MB)')
        return True

    except Exception as e:
        print(f'FAIL: {e}')
        return False


def main():
    if len(sys.argv) < 2:
        print('Usage: python qmc_decrypt.py <file_or_directory> [output_directory]')
        sys.exit(1)

    input_path = sys.argv[1]
    supported_exts = ('.mgg', '.mgg0', '.mgg1', '.mggl', '.mflac', '.mflac0',
                      '.qmc0', '.qmc2', '.qmc3', '.qmcflac', '.qmcogg',
                      '.bkcmp3', '.bkcflac', '.tkm')

    if os.path.isfile(input_path):
        output_path = sys.argv[2] if len(sys.argv) > 2 else None
        decrypt_file(input_path, output_path)

    elif os.path.isdir(input_path):
        output_dir = sys.argv[2] if len(sys.argv) > 2 else os.path.join(input_path, 'decrypted')
        os.makedirs(output_dir, exist_ok=True)

        count = 0
        success = 0
        failed = []

        files = []
        for root, _, fnames in os.walk(input_path):
            for fn in fnames:
                if fn.lower().endswith(supported_exts):
                    files.append(os.path.join(root, fn))

        print(f'Found {len(files)} encrypted files in {input_path}')
        print(f'Output directory: {output_dir}')
        print()

        for i, fpath in enumerate(files, 1):
            fname = os.path.basename(fpath)
            out_name = os.path.splitext(fname)[0]
            # We'll detect extension after decryption
            try:
                with open(fpath, 'rb') as f:
                    data = f.read()
                decoder = QmcDecoder(data)
                decrypted = decoder.decrypt()
                detected_ext = detect_ext(decrypted)
                out_path = os.path.join(output_dir, out_name + '.' + detected_ext)
                with open(out_path, 'wb') as f:
                    f.write(decrypted)
                size_mb = len(decrypted) / (1024 * 1024)
                print(f'  [{i}/{len(files)}] {fname} -> {detected_ext} ({size_mb:.1f}MB)')
                success += 1
            except Exception as e:
                print(f'  [{i}/{len(files)}] {fname} -> FAIL: {e}')
                failed.append(fname)

        print(f'\nDone: {success}/{len(files)} decrypted successfully')
        if failed:
            print(f'Failed files: {len(failed)}')
            for f in failed[:10]:
                print(f'  - {f}')
            if len(failed) > 10:
                print(f'  ... and {len(failed) - 10} more')


if __name__ == '__main__':
    main()

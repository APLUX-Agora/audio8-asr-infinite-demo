"""Audio8 models.json packaging contract; no inference or application policy."""
import json
import os
from pathlib import Path, PurePosixPath

COMMON_FILES = {
    'config': 'frontend/config.json', 'rows_const': 'frontend/rows_const.npy',
    'mel_filters': 'mel_filters.npy', 'token_bytes': 'token_bytes.json',
    'encoder_prefix_kv': 'prefix/encoder.bin', 'decoder_prefix_kv_zh': 'prefix/decoder_zh.bin',
    'decoder_prefix_kv_en': 'prefix/decoder_en.bin', 'embedding': 'embedding.bin',
    'rotation': 'rotation.npy', 'vad_W': 'semantic_vad/weight.npy',
    'vad_b': 'semantic_vad/bias.npy', 'vad_meta': 'semantic_vad/config.json',
}
GRAPHS = {'encoder': 'encoder.aidem', 'adapter': 'adapter.aidem',
          'decoder_1': 'decoder_1.aidem', 'decoder_2': 'decoder_2.aidem'}
SOCS = ('qcs8550', 'qcs8625', 'qcs8275', 'qcs9075')


def contained(root, name):
    if not isinstance(name, str) or not name or '\\' in name:
        raise ValueError('invalid relative model path')
    p = PurePosixPath(name)
    if p.is_absolute() or any(x in ('.', '..') for x in name.split('/')) or str(p) != name:
        raise ValueError('invalid relative model path')
    path = root / name
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError('model resource escapes package root: ' + name)
    return path


def inspect(root):
    root = Path(root)
    try:
        doc = json.loads((root / 'models.json').read_text(encoding='utf-8'))
        clock = doc['audio_clock_ms']
        if (type(doc['format_version']) is not int or doc['format_version'] != 1
                or type(clock) is not int or clock not in (80, 160)
                or doc['model_name'] != f'Audio8-ASR-Infinite-{clock}ms'):
            raise ValueError('unsupported models.json format, model identity or audio clock')
        spec = doc['tensor_metadata']['embedding.bin']
        if (spec['dtype'] != 'float32-le' or spec['shape'] != [151936, 2048]
                or spec['layout'] != 'row-major'):
            raise ValueError('unsupported embedding metadata')
        explicit = os.environ.get('A8_TARGET')
        declared, candidates = set(), []
        if not isinstance(doc['targets'], list):
            raise ValueError('models.json targets must be a list')
        for target in doc['targets']:
            if target['soc'] not in SOCS or target['qnn_version'] != '2.48':
                raise ValueError('unsupported SoC or QNN version')
            tid = target['soc'] + '_qnn248'
            folder = target['directory']
            if folder != 'targets/' + tid or tid in declared:
                raise ValueError('invalid or duplicate model target')
            declared.add(tid)
            contained(root, folder)
            if explicit is not None and explicit != tid:
                continue
            files = {key: folder + '/' + name for key, name in GRAPHS.items()}
            if all(contained(root, p).is_file() for p in files.values()):
                candidates.append(files)
        if len(candidates) != 1:
            raise ValueError('no complete selected target; download its SoC directory' if not candidates else
                             'multiple installed targets; select one with A8_TARGET=<soc>_qnn248')
        layout = dict(COMMON_FILES, **candidates[0])
        for name in layout.values():
            if not contained(root, name).is_file():
                raise ValueError('missing model file: ' + name)
        if (root / 'embedding.bin').stat().st_size != 151936 * 2048 * 4:
            raise ValueError('incorrect-size embedding.bin')
        return {'format': 3, 'clocks': {str(clock): layout},
                'extras': {'tokenizer': 'tokenizer.json'}}
    except (KeyError, TypeError, OSError, json.JSONDecodeError) as error:
        raise ValueError('missing or invalid models.json package: ' + str(error)) from error

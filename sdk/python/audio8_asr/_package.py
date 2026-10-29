"""Audio8 models.json packaging contract; no inference or application policy."""
import json
import os
from pathlib import Path, PurePosixPath

# Resource roles are model semantics; file names and locations come only from models.json.
COMMON_ROLES = {
    'config': ('frontend_config',), 'rows_const': ('audio_constants',),
    'mel_filters': ('mel_filters',), 'token_bytes': ('vocabulary',),
    'encoder_prefix_kv': ('prefix', 'encoder'), 'decoder_prefix_kv_zh': ('prefix', 'decoder_zh'),
    'decoder_prefix_kv_en': ('prefix', 'decoder_en'), 'embedding': ('token_vectors', 'path'),
    'rotation': ('rotation',), 'vad_W': ('semantic_vad', 'weight'),
    'vad_b': ('semantic_vad', 'bias'), 'vad_meta': ('semantic_vad', 'config'),
}
GRAPH_ROLES = ('encoder', 'adapter', 'decoder_1', 'decoder_2')
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
        if (type(doc['format_version']) is not int or doc['format_version'] != 2
                or type(clock) is not int or clock not in (80, 160)
                or doc['model_name'] != f'Audio8-ASR-Infinite-{clock}ms'):
            raise ValueError('unsupported models.json format, model identity or audio clock')
        resources = doc['resources']
        spec = resources['token_vectors']
        if (spec['dtype'] != 'float32-le' or spec['shape'] != [151936, 2048]
                or spec['layout'] != 'row-major'):
            raise ValueError('unsupported embedding metadata')
        layout = {}
        for role, keys in COMMON_ROLES.items():
            value = resources
            for key in keys:
                value = value[key]
            contained(root, value)
            layout[role] = value
        tokenizer = resources['tokenizer']
        if not contained(root, tokenizer).is_file():
            raise ValueError('missing tokenizer resource')
        explicit = os.environ.get('A8_TARGET')
        declared, candidates = set(), []
        if not isinstance(doc['targets'], list):
            raise ValueError('models.json targets must be a list')
        for target in doc['targets']:
            if target['soc'] not in SOCS or target['qnn_version'] != '2.48':
                raise ValueError('unsupported SoC or QNN version')
            tid = target['soc'] + '_qnn248'
            folder = target['directory']
            if tid in declared:
                raise ValueError('invalid or duplicate model target')
            declared.add(tid)
            contained(root, folder)
            files = {role: target['files'][role] for role in GRAPH_ROLES}
            for path in files.values():
                resolved = contained(root, path)
                if not resolved.resolve().is_relative_to((root / folder).resolve()):
                    raise ValueError('graph resource is outside its declared target directory')
            if explicit is not None and explicit != tid:
                continue
            if all(contained(root, p).is_file() and (root / p).stat().st_size > 0 for p in files.values()):
                candidates.append(files)
        if len(candidates) != 1:
            raise ValueError('no complete selected target; download its SoC directory' if not candidates else
                             'multiple installed targets; select one with A8_TARGET=<soc>_qnn248')
        layout.update(candidates[0])
        for name in layout.values():
            if not contained(root, name).is_file():
                raise ValueError('missing model file: ' + name)
        if (root / layout['embedding']).stat().st_size != 151936 * 2048 * 4:
            raise ValueError('incorrect-size embedding.bin')
        return {'format': 3, 'clocks': {str(clock): layout},
                'extras': {'tokenizer': tokenizer}}
    except (KeyError, TypeError, OSError, json.JSONDecodeError) as error:
        raise ValueError('missing or invalid models.json package: ' + str(error)) from error

#!/usr/bin/env python3
"""Run explicit 2D maxima using a selected local Fiji; Python standard library only."""
import argparse
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone


def now():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def save(path, value):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n')
    temporary.replace(path)


def discover(explicit=None):
    if explicit:
        root = Path(explicit).expanduser().resolve(strict=True)
    else:
        home = Path.home()
        possibilities = [Path('/Applications/Fiji.app'), home/'Applications/Fiji.app',
                         home/'Desktop/Fiji.app', home/'Desktop/Fiji/Fiji.app']
        found = sorted({p.resolve() for p in possibilities if (p/'jars').is_dir()})
        if len(found) != 1:
            raise ValueError('Specify --fiji: expected one local installation, found ' + str(found))
        root = found[0]
    jars = sorted((root/'jars').glob('ij-*.jar'))
    if len(jars) != 1:
        raise ValueError('Expected exactly one ImageJ ij-*.jar under ' + str(root/'jars'))
    executables = {}
    for name in ('java', 'javac'):
        suffix = '.exe' if os.name == 'nt' else ''
        bundled = sorted(p.resolve() for p in (root/'java').glob('**/bin/' + name + suffix)
                         if os.access(str(p), os.X_OK))
        # A JDK can contain both bin/java and its own nested jre/bin/java.
        # Treat those as one installation, preferring the outer JDK executable.
        bundled = [p for p in bundled if not any(q != p and q.parent.parent in p.parents for q in bundled)]
        if len(bundled) > 1:
            # Multiple bundled versions are not a basis for a silent choice.
            raise ValueError('Multiple bundled ' + name + ' executables; select a compatible installation')
        found = str(bundled[0]) if bundled else shutil.which(name)
        if not found:
            raise ValueError('No ' + name + ' found in Fiji or PATH')
        executables[name] = found
    return dict(fiji=str(root), ij_jar=str(jars[0]), **executables)


def call(command, timeout=180):
    result = subprocess.run(command, capture_output=True, text=True, timeout=timeout, shell=False)
    if result.returncode:
        raise RuntimeError('Process failed (' + str(result.returncode) + '):\n' + result.stdout + result.stderr)
    return result.stdout.strip(), result.stderr.strip()


def compile_helper(env, classes):
    source = Path(__file__).with_name('FijiFoci.java')
    call([env['javac'], '-encoding', 'UTF-8', '-cp', env['ij_jar'], '-d', str(classes), str(source)])
    return [env['java'], '-Djava.awt.headless=true', '-cp', os.pathsep.join([str(classes), env['ij_jar']]), 'FijiFoci']


def configuration(path):
    config = json.loads(Path(path).read_text())
    required = {'image_id', 'detection_image', 'review_image', 'nuclei_labels', 'amplitude',
                'prominence', 'min_distance_px', 'exclude_image_edges', 'display_min', 'display_max',
                'units', 'preprocessing'}
    if not isinstance(config, dict) or set(config) != required:
        raise ValueError('Configuration keys must be exactly: ' + ', '.join(sorted(required)))
    if not isinstance(config['image_id'], str) or not re.fullmatch(r'[A-Za-z0-9_-]+', config['image_id']):
        raise ValueError('image_id must use safe letters, digits, underscores or hyphens')
    for key in ('amplitude', 'prominence', 'min_distance_px', 'display_min', 'display_max'):
        if type(config[key]) not in (float, int) or not math.isfinite(config[key]):
            raise ValueError(key + ' must be a finite number')
    if config['prominence'] < 0 or config['min_distance_px'] < 0:
        raise ValueError('Prominence and distance must be nonnegative')
    if config['display_max'] <= config['display_min']:
        raise ValueError('Display maximum must exceed minimum')
    if type(config['exclude_image_edges']) is not bool:
        raise ValueError('exclude_image_edges must be a boolean')
    for key in ('units', 'preprocessing'):
        if not isinstance(config[key], str) or not config[key].strip():
            raise ValueError(key + ' must be a nonempty description')
    for key in ('detection_image', 'review_image', 'nuclei_labels'):
        if key == 'nuclei_labels' and config[key] is None:
            continue
        if not isinstance(config[key], str) or not Path(config[key]).is_absolute():
            raise ValueError(key + ' must be an absolute file path')
        file = Path(config[key]).resolve(strict=True)
        if not file.is_file():
            raise ValueError(key + ' is not a file')
        config[key] = str(file)
    return config


@contextmanager
def prepared_helper(env):
    """Compile and probe once; callers must finish jobs before leaving this context."""
    with tempfile.TemporaryDirectory(prefix='fiji-foci-') as tmp:
        base = compile_helper(env, tmp)
        yield {'command': base, 'environment': dict(env),
               'imagej_version': call(base + ['probe'])[0],
               'java_version': '\n'.join(call([env['java'], '-version'])),
               'helper_sha256': {p.name: sha(p) for p in
                                (Path(__file__), Path(__file__).with_name('FijiFoci.java'))}}


def run(env, config, out, timeout, prepared=None):
    if prepared is None:
        with prepared_helper(env) as helper:
            return run(env, config, out, timeout, prepared=helper)
    if prepared['environment'] != env or any(
            sha(Path(__file__).with_name(name)) != digest
            for name, digest in prepared['helper_sha256'].items()):
        raise ValueError('Prepared helper no longer matches environment/source')
    out = Path(out).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=False)
    paths = [config[k] for k in ('detection_image', 'review_image', 'nuclei_labels') if config[k]]
    record = {'status': 'started', 'started_utc': now(), 'environment': env,
              'input_sha256': {p: sha(p) for p in paths},
              'helper_sha256': {p.name: sha(p) for p in (Path(__file__), Path(__file__).with_name('FijiFoci.java'))},
              'coordinate_convention': 'top-left origin; zero-based x,y pixel indices',
              'validation': 'Execution checks only; biological accuracy is not established.'}
    save(out/'configuration.json', config)
    record['configuration_sha256'] = sha(out/'configuration.json')
    save(out/'execution.json', record)
    try:
        base = prepared['command']
        record['imagej_version'] = prepared['imagej_version']
        record['java_version'] = prepared['java_version']
        command = base + [config['image_id'], config['detection_image'], config['review_image'],
            config['nuclei_labels'] or '-', str(config['amplitude']), str(config['prominence']),
            str(config['min_distance_px']), str(config['exclude_image_edges']).lower(),
            str(config['display_min']), str(config['display_max']), str(out), config['units'], config['preprocessing']]
        record['command'] = command
        save(out/'execution.json', record)
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout, shell=False)
        (out/'stdout.txt').write_text(result.stdout)
        (out/'stderr.txt').write_text(result.stderr)
        record['returncode'] = result.returncode
        if result.returncode:
            raise RuntimeError('Fiji failed: ' + result.stderr.strip())
        expected = ['foci.csv', 'foci.zip', 'review.tif', 'preview.png']
        if config['nuclei_labels']:
            expected += ['nuclei.csv', 'nuclei.zip', 'nuclei_labels.tif']
        if any(not (out/p).is_file() or (out/p).stat().st_size == 0 for p in expected):
            raise RuntimeError('An expected output is missing or empty')
        if any(sha(p) != digest for p, digest in record['input_sha256'].items()):
            raise RuntimeError('Source content changed during execution')
        record['output_sha256'] = {p: sha(out/p) for p in expected}
        record['status'] = 'complete'
    except Exception as error:
        record['status'] = 'failed'
        record['error'] = str(error)
        if isinstance(error, subprocess.TimeoutExpired):
            for stream in ('stdout', 'stderr'):
                value = getattr(error, stream, None) or ''
                if isinstance(value, bytes):
                    value = value.decode('utf-8', errors='replace')
                (out/(stream+'.txt')).write_text(value)
        raise
    finally:
        record['finished_utc'] = now()
        save(out/'execution.json', record)
    return record


def batch(env, config_paths, out, timeout=300, workers=1):
    """Validate all jobs first, then reuse one compilation with bounded subprocesses."""
    if not 1 <= workers <= 8 or timeout <= 0:
        raise ValueError('workers must be 1–8 and timeout must be positive')
    if not config_paths:
        raise ValueError('Batch requires at least one configuration')
    configs = [configuration(path) for path in config_paths]
    ids = [c['image_id'] for c in configs]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate image_id in batch; use unique IDs for sensitivity variants')
    out = Path(out).expanduser().resolve()
    if any((out / image_id).exists() for image_id in ids):
        raise ValueError('Batch refuses existing image outputs; use a new run or verify checkpoints externally')
    out.mkdir(parents=True, exist_ok=True)
    with prepared_helper(env) as helper:
        def execute(config):
            destination = out/config['image_id']
            try:
                run(env, config, destination, timeout, prepared=helper)
                return {'image_id': config['image_id'], 'status': 'complete', 'output': str(destination)}
            except (ValueError, OSError, RuntimeError, subprocess.SubprocessError) as error:
                return {'image_id': config['image_id'], 'status': 'failed', 'output': str(destination),
                        'error': str(error)}
        with ThreadPoolExecutor(max_workers=workers) as pool:
            results = list(pool.map(execute, configs))
    return {'status': 'failed' if any(r['status']=='failed' for r in results) else 'complete',
            'images': results, 'workers': workers}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    doctor = sub.add_parser('doctor', help='Discover, compile and probe local Fiji')
    doctor.add_argument('--fiji')
    execute = sub.add_parser('run', help='Run one configured scalar 2D image into a new folder')
    execute.add_argument('--fiji')
    execute.add_argument('--config', required=True)
    execute.add_argument('--out', required=True)
    execute.add_argument('--timeout', type=int, default=300)
    multi = sub.add_parser('batch', help='Reuse one compilation across configured 2D images')
    multi.add_argument('--fiji')
    multi.add_argument('--configs', nargs='+', required=True, help='JSON configuration files')
    multi.add_argument('--out', required=True, help='Parent folder; child folders use image_id')
    multi.add_argument('--timeout', type=int, default=300)
    multi.add_argument('--workers', type=int, default=1, help='Concurrent image processes, 1–8; size to memory')
    args = parser.parse_args()
    env = discover(args.fiji)
    if args.action == 'doctor':
        with tempfile.TemporaryDirectory(prefix='fiji-doctor-') as tmp:
            base = compile_helper(env, tmp)
            env['imagej_version'] = call(base + ['probe'])[0]
            env['java_version'] = '\n'.join(call([env['java'], '-version']))
        print(json.dumps(env, indent=2))
    elif args.action == 'batch':
        result = batch(env, args.configs, args.out, args.timeout, args.workers)
        print(json.dumps(result, indent=2))
        if result['status'] == 'failed':
            sys.exit(1)
    else:
        if args.timeout <= 0:
            raise ValueError('Timeout must be positive')
        result = run(env, configuration(args.config), args.out, args.timeout)
        print(json.dumps({'status': result['status'], 'output': str(Path(args.out).resolve())}))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, RuntimeError, subprocess.SubprocessError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)

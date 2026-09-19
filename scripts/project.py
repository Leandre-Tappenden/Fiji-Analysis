#!/usr/bin/env python3
"""Small offline project, QC/decision log and report helper; Python standard library only."""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import html
import itertools
import json
from pathlib import Path
import re
import shutil
import sys
from urllib.parse import quote
import uuid


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write(path, data):
    path = Path(path)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False)+'\n', encoding='utf-8')
    tmp.replace(path)


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()


def internal(root, relative):
    root = root.resolve()
    path = (root/relative).resolve()
    if root not in path.parents or path == root:
        raise ValueError('Artifact must be a file inside the run: ' + str(relative))
    return path


def record_dir(root):
    """Read old runs in place; new runs keep technical records out of the main view."""
    modern = root/'Additional_material/Run_records'
    return modern if (modern/'brief.json').exists() else root/'provenance'


def init(args):
    source = Path(args.source).expanduser().resolve(strict=True)
    root = Path(args.run).expanduser().resolve()
    if source == root or source in root.parents:
        raise ValueError('Choose a run outside the raw source directory')
    root.mkdir(parents=True, exist_ok=False)
    for folder in ('Reports', 'R_scripts', 'Tables/Main_results',
                   'Tables/Segmentation_checks', 'Tables/Counting_sensitivity', 'Tables/Statistics',
                   'QC_images/Channel_checks', 'QC_images/Segmentation', 'QC_images/Foci_counts',
                   'Analysis_scripts', 'Graphs', 'Additional_material/Editable_masks_and_ROIs',
                   'Additional_material/Run_records'):
        (root/folder).mkdir(parents=True, exist_ok=True)
    brief = {'schema_version': 3, 'run_id': root.name, 'title': args.title,
             'source': str(source), 'created_utc': timestamp(), 'output_mode': args.mode,
             'primary_artifact': None, 'status': 'draft',
             'validation': 'Not yet assessed', 'summary': [], 'measurement': {}, 'design': {},
             'channel_mapping': [], 'open_questions': []}
    write(root/'Additional_material/Run_records/brief.json', brief)
    write(record_dir(root)/'artifacts.json', [])
    (record_dir(root)/'events.jsonl').touch()
    if args.prompt:
        shutil.copyfile(Path(args.prompt).resolve(strict=True), record_dir(root)/'original_prompt.txt')
    render(root)
    return {'run': str(root), 'status': 'draft', 'mode': args.mode}


def event(args, root):
    value = read(args.json)
    if not isinstance(value, dict):
        raise ValueError('Event must be a JSON object')
    required = ({'stage', 'code', 'severity', 'scope', 'finding', 'action', 'affected_metrics'}
                if args.kind == 'quality' else
                {'stage', 'parameter', 'value', 'units', 'scope', 'reason', 'evidence', 'chosen_by'})
    if not required.issubset(value):
        raise ValueError('Missing event fields: ' + ', '.join(sorted(required-set(value))))
    for key in required - {'value', 'evidence', 'affected_metrics'}:
        if not isinstance(value[key], str) or not value[key].strip():
            raise ValueError('Event ' + key + ' must be a nonempty string')
    if args.kind == 'quality':
        if value['severity'] not in ('info', 'warning', 'error'):
            raise ValueError('severity must be info, warning or error')
        if not isinstance(value['affected_metrics'], list):
            raise ValueError('affected_metrics must be a list')
    record = dict(value, kind=args.kind, event_id=str(uuid.uuid4()), timestamp_utc=timestamp())
    brief = read(record_dir(root)/'brief.json')
    record['run_id'] = brief['run_id']
    parameters = (root/'Analysis_scripts/parameters.json' if brief.get('schema_version', 1) >= 3
                  else record_dir(root)/'parameters.json')
    if parameters.exists():
        record['configuration_sha256'] = digest(parameters)
    with (record_dir(root)/'events.jsonl').open('a', encoding='utf-8') as f:
        f.write(json.dumps(record, ensure_ascii=False, allow_nan=False)+'\n')
    if not getattr(args, 'no_render', False):
        render(root)
    return {'event_id': record['event_id'], 'kind': args.kind}


def add(args, root):
    source = Path(args.file).expanduser().resolve(strict=True)
    if not source.is_file():
        raise ValueError('Register one file at a time')
    locations = {'preview': 'review/images', 'table': 'tables', 'figure': 'figures',
                 'annotation': 'review/annotations', 'provenance': 'provenance'}
    if args.role == 'preview':
        if source.suffix.lower() not in ('.png', '.jpg', '.jpeg'):
            raise ValueError('Preview must be PNG or JPEG')
        if not args.stage or not args.scaling or not args.image_id:
            raise ValueError('Preview requires --stage, --scaling and --image-id')
    brief = read(record_dir(root)/'brief.json')
    category = getattr(args, 'category', None)
    graph_id = getattr(args, 'graph_id', None)
    uses = getattr(args, 'uses', None) or []
    if graph_id and not re.fullmatch(r'[A-Za-z0-9_-]+', graph_id):
        raise ValueError('graph-id must use safe letters/digits/underscore/hyphen')
    if brief.get('schema_version', 1) >= 2:
        if args.role == 'table':
            category = category or 'main_results'
            if category not in ('main_results', 'qc_segmentation', 'qc_counting_sensitivity', 'stats'):
                raise ValueError('Unknown CSV category')
        elif args.role == 'preview':
            category = category or {'channels': 'channel_testing', 'channel identification': 'channel_testing',
                                    'segmentation': 'segmentation'}.get(args.stage.lower(), 'foci_counts')
            if category not in ('channel_testing', 'segmentation', 'foci_counts'):
                raise ValueError('Unknown QC image category')
        elif category:
            raise ValueError('category applies only to tables and previews')
        locations = {'table': 'csv/' + (category or 'main_results'),
                     'preview': 'qc_images/' + (category or 'foci_counts'),
                     'figure': 'graphs', 'annotation': 'annotations', 'provenance': 'provenance',
                     'r_script': 'r_scripts', 'analysis_script': 'analysis_scripts', 'guide': 'analysis_scripts'}
    else:
        locations.update(r_script='r_scripts', analysis_script='analysis_scripts', guide='analysis_scripts')
        if category:
            raise ValueError('Categories require a version-2 run; keep legacy paths unchanged')
    if brief.get('schema_version', 1) >= 3:
        tables = {'main_results': 'Main_results', 'qc_segmentation': 'Segmentation_checks',
                  'qc_counting_sensitivity': 'Counting_sensitivity', 'stats': 'Statistics'}
        previews = {'channel_testing': 'Channel_checks', 'segmentation': 'Segmentation',
                    'foci_counts': 'Foci_counts'}
        locations = {'table': 'Tables/' + tables.get(category, 'Main_results'),
                     'preview': 'QC_images/' + previews.get(category, 'Foci_counts'),
                     'figure': 'Graphs', 'annotation': 'Additional_material/Editable_masks_and_ROIs',
                     'provenance': 'Additional_material/Run_records', 'r_script': 'R_scripts',
                     'analysis_script': 'Analysis_scripts', 'guide': 'Reports'}
    artifacts = read(record_dir(root)/'artifacts.json')
    registered = {a['path'] for a in artifacts}
    for dependency in uses:
        if Path(dependency).is_absolute() or not internal(root, dependency).is_file():
            raise ValueError('Dependency must be an existing run-relative file: ' + dependency)
        if dependency not in registered:
            raise ValueError('Register dependency first: ' + dependency)
    if args.primary:
        mode = brief['output_mode']
        if not ((mode == 'table' and args.role == 'table' and source.suffix.lower() == '.csv') or
                (mode == 'figures' and args.role == 'figure' and source.suffix.lower() in ('.pdf', '.png', '.svg'))):
            raise ValueError('--primary must match the chosen table/figures mode')
    destination = Path(locations[args.role])
    if args.image_id:
        if not re.fullmatch(r'[A-Za-z0-9_-][A-Za-z0-9_. +()-]*', args.image_id):
            raise ValueError('image-id must be a safe source-derived filename stem (no path separators)')
        if args.role in ('preview', 'annotation'):
            destination /= args.image_id
    relative = (destination/source.name).as_posix()
    target = internal(root, relative)
    artifacts = read(record_dir(root)/'artifacts.json')
    if any(a['path'] == relative for a in artifacts):
        raise ValueError('Artifact already registered; use a new filename for a revision')
    if target != source:
        if target.exists():
            raise ValueError('Refusing to overwrite existing artifact: ' + relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    artifact = {'path': relative, 'role': args.role, 'caption': args.caption,
                'stage': args.stage or '', 'image_id': args.image_id or '',
                'scaling': args.scaling or '', 'category': category or '',
                'graph_id': graph_id or '', 'uses': uses, 'sha256': digest(target), 'registered_utc': timestamp()}
    artifacts.append(artifact)
    write(record_dir(root)/'artifacts.json', artifacts)
    if args.primary:
        brief['primary_artifact'] = relative
        write(record_dir(root)/'brief.json', brief)
    if not getattr(args, 'no_render', False):
        render(root)
    return artifact


def fmt(value):
    return json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else str(value)


def escaped(value):
    return html.escape(fmt(value), quote=True)


def table(rows, fields):
    if not rows:
        return '<p class="muted">None recorded.</p>'
    head = ''.join('<th>'+escaped(k.replace('_', ' '))+'</th>' for k in fields)
    body = ''.join('<tr>'+''.join('<td>'+escaped(r.get(k, ''))+'</td>' for k in fields)+'</tr>' for r in rows)
    return '<div class="scroll"><table><thead><tr>'+head+'</tr></thead><tbody>'+body+'</tbody></table></div>'


def artifact_link(artifact):
    return ('<a href="'+quote(artifact['path'])+'">'+escaped(artifact['path'])+'</a> — '+
            escaped(artifact['caption']))


def brief_section(value):
    if not value:
        return '<p class="muted">Not recorded.</p>'
    if isinstance(value, dict):
        return table([{'item': key, 'details': val} for key,val in value.items()], ['item','details'])
    if isinstance(value, list):
        if all(isinstance(item, dict) for item in value):
            return table(value, list(dict.fromkeys(k for item in value for k in item)))
        return '<ul>'+''.join('<li>'+escaped(item)+'</li>' for item in value)+'</ul>'
    return '<p>'+escaped(value)+'</p>'


def export_events(root, events, kind, name):
    records = [e for e in events if e['kind'] == kind]
    fields = list(dict.fromkeys(k for e in records for k in e)) or ['event_id', 'timestamp_utc', 'kind']
    with (record_dir(root)/name).open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows({k: fmt(v) for k,v in e.items()} for e in records)


def render(root):
    brief = read(record_dir(root)/'brief.json')
    artifacts = read(record_dir(root)/'artifacts.json')
    events = [json.loads(line) for line in (record_dir(root)/'events.jsonl').read_text().splitlines() if line.strip()]
    for a in artifacts:
        artifact_path = internal(root, a['path'])
        if not artifact_path.is_file():
            raise ValueError('Registered artifact is missing: ' + a['path'])
        if digest(artifact_path) != a['sha256']:
            raise ValueError('Registered artifact changed; preserve it as an explicit revision: ' + a['path'])
    for kind, name in (('quality', 'quality_log.csv'), ('decision', 'decision_log.csv')):
        export_events(root, events, kind, name)
    registered = {a['path'] for a in artifacts}
    for a in artifacts:
        for dependency in a.get('uses', []):
            if dependency not in registered:
                raise ValueError('Register dependency before rendering: ' + dependency)
    primary = brief.get('primary_artifact')
    if primary and not any(a['path'] == primary for a in artifacts):
        raise ValueError('Primary artifact must be registered')
    if brief['status'] == 'complete':
        if not artifacts or not brief.get('summary'):
            raise ValueError('Complete reports require results and a summary')
        if brief['output_mode'] != 'report' and not primary:
            raise ValueError('Complete table/figures mode requires its primary artifact')
    parts = ['<!doctype html><html lang="en"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width,initial-scale=1">',
        '<title>'+escaped(brief['title'])+'</title><style>',
        'body{font:16px/1.55 system-ui,sans-serif;color:#24343b;max-width:1100px;margin:40px auto;padding:0 24px}',
        'h1{font-size:30px}h2{font-size:21px;margin-top:32px}a{color:#126273}.muted{color:#596a70}',
        '.meta{background:#eff5f5;padding:16px;border-radius:8px}.scroll{overflow:auto}',
        'table{border-collapse:collapse;width:100%;font-size:14px}th,td{padding:9px;text-align:left;border-bottom:1px solid #dbe3e5;vertical-align:top}',
        'figure{margin:24px 0}img{max-width:100%;height:auto;border:1px solid #dbe3e5}figcaption{font-size:14px}',
        'details{margin:18px 0}summary{cursor:pointer;font-weight:600}</style></head><body>',
        '<h1>'+escaped(brief['title'])+'</h1>',
        '<div class="meta"><b>Status:</b> '+escaped(brief['status'])+'<br><b>Validation:</b> '+escaped(brief['validation'])+
        '<br><b>Run:</b> '+escaped(brief['run_id'])+'</div>']
    sections = [('summary', 'Summary'), ('design', 'Experiment and question'),
                ('channels', 'Channel attribution'), ('results', 'Results and graphs'),
                ('method', 'Method and sensitivity'), ('image-checks', 'QC images'),
                ('quality', 'Data quality'), ('decisions', 'Measurement decisions'),
                ('files', 'Reproduction and files')]
    if (record_dir(root)/'original_prompt.txt').is_file():
        sections.append(('prompt', 'Original request'))
    parts.append('<nav aria-label="Contents"><h2>Contents</h2><ul>' + ''.join(
        '<li><a href="#'+key+'">'+label+'</a></li>' for key,label in sections) + '</ul></nav>')
    parts.append('<h2 id="summary">Summary</h2>')
    if primary:
        parts.append('<p><a href="'+quote(primary)+'"><b>Open main '+escaped(brief['output_mode'])+' output</b></a></p>')
    parts += ['<p>'+escaped(s)+'</p>' for s in brief.get('summary', [])]
    if not brief.get('summary'):
        parts.append('<p class="muted">Analysis is being prepared. No scientific result has been recorded.</p>')
    parts.append('<h2 id="design">Experiment and question</h2>' + brief_section(brief.get('design')))
    parts.append('<h2 id="channels">Channel attribution</h2>' + brief_section(brief.get('channel_mapping')))
    parts.append('<h2 id="results">Results and graphs</h2>')
    for a in (a for a in artifacts if a['role'] == 'figure'):
        parts.append('<figure>')
        if Path(a['path']).suffix.lower() in ('.png', '.jpg', '.jpeg', '.svg'):
            parts.append('<img loading="lazy" src="'+quote(a['path'])+'" alt="'+escaped(a['caption'])+'">')
        parts.append('<figcaption>'+artifact_link(a)+'</figcaption>')
        if a.get('graph_id'):
            parts.append('<p>Graph: '+escaped(a['graph_id'])+'</p>')
        dependencies = set(a.get('uses', []))
        if a.get('graph_id'):
            for script in artifacts:
                if script['role'] == 'r_script' and script.get('graph_id') == a['graph_id']:
                    dependencies.add(script['path'])
                    dependencies.update(script.get('uses', []))
        if dependencies:
            parts.append('<p>Code and data: '+ ' · '.join(
                '<a href="'+quote(path)+'">'+escaped(path)+'</a>' for path in sorted(dependencies))+'</p>')
        parts.append('</figure>')
    csv_artifacts = [a for a in artifacts if a['role']=='table' and a['path'].lower().endswith('.csv')]
    if csv_artifacts:
        chosen = next((a for a in csv_artifacts if a['path']==primary), csv_artifacts[0])
        with internal(root, chosen['path']).open(newline='', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            rows = list(itertools.islice(reader, 12))
            fields = reader.fieldnames or []
        parts += ['<h2>Results preview</h2><p class="muted">First 12 rows; use the CSV for the full table.</p>', table(rows, fields)]
    parts.append('<h2 id="method">Method and sensitivity</h2>'+brief_section(brief.get('measurement')))
    if brief.get('open_questions'):
        parts.append('<h3>Unresolved questions</h3>'+brief_section(brief['open_questions']))
    previews = [a for a in artifacts if a['role']=='preview']
    parts.append('<h2 id="image-checks">QC images</h2>')
    if previews:
        for a in previews:
            parts.append('<figure><a href="'+quote(a['path'])+'"><img loading="lazy" src="'+quote(a['path'])+
                '" alt="'+escaped(a['caption'])+'"></a><figcaption><b>'+escaped(a['stage'])+' · '+
                escaped(a['image_id'])+'</b> — '+escaped(a['caption'])+'<br>Display: '+escaped(a['scaling'])+'<br>'+artifact_link(a)+'</figcaption></figure>')
    quality = [e for e in events if e['kind']=='quality']
    decisions = [e for e in events if e['kind']=='decision']
    parts += ['<h2 id="quality">Data quality</h2>', table(quality, ['severity','scope','finding','action','affected_metrics']),
              '<h2 id="decisions">Measurement decisions</h2>', '<details><summary>Detailed settings and decision history</summary>'+table(decisions, ['parameter','value','units','scope','reason','chosen_by'])+'</details>']
    parts.append('<h2 id="files">Reproduction and files</h2>')
    for guide in (a for a in artifacts if a['role'] == 'guide'):
        parts.append('<p>'+artifact_link(guide)+'</p>')
    groups = [('Graphs', ['figure']), ('R scripts', ['r_script']), ('Results tables', ['table']),
              ('Analysis scripts and guides', ['analysis_script', 'guide']),
              ('QC images', ['preview']), ('Editable masks and ROIs', ['annotation']),
              ('Additional run records', ['provenance'])]
    for title, roles in groups:
        selected = [a for a in artifacts if a['role'] in roles]
        if selected:
            parts.append('<details><summary>'+title+' ('+str(len(selected))+')</summary><ul>')
            parts.extend('<li>'+artifact_link(a)+'</li>' for a in selected)
            parts.append('</ul></details>')
    parts.append('<details><summary>Analysis records</summary><ul>')
    for path, label in [('provenance/brief.json','Analysis brief'),('provenance/quality_log.csv','Full quality log'),
                        ('provenance/decision_log.csv','Full decision log'),('provenance/events.jsonl','Event history'),
                        ('provenance/artifacts.json','Artifact registry')]:
        path = (record_dir(root)/Path(path).name).relative_to(root).as_posix()
        parts.append('<li><a href="'+quote(path)+'">'+label+' — '+path+'</a></li>')
    parts.append('</ul></details>')
    prompt = record_dir(root)/'original_prompt.txt'
    if prompt.is_file():
        parts.append('<h2 id="prompt">Original request</h2><pre style="white-space:pre-wrap">'+
                     escaped(prompt.read_text(encoding='utf-8'))+'</pre>')
    parts.append('</body></html>')
    report = root/'report.html'
    document = '\n'.join(parts)
    if brief.get('schema_version', 1) >= 3:
        report = root/'Reports/Experiment_report.html'
        # Artifact paths are stored relative to the run; links are relative to Reports/.
        document = re.sub(r'(href|src)="([^"#][^"]*)"',
                          lambda m: m[1]+'="../'+m[2]+'"', document)
    report.write_text(document, encoding='utf-8')
    return {'report': str(report), 'primary': str(root/primary) if primary else str(report)}



def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    p = sub.add_parser('init', help='Create a new named run, draft brief and report')
    p.add_argument('--run', required=True); p.add_argument('--source', required=True)
    p.add_argument('--title', required=True); p.add_argument('--mode', choices=['report','table','figures'], default='report')
    p.add_argument('--prompt')
    p = sub.add_parser('event', help='Append a structured QC finding or measurement decision')
    p.add_argument('--run', required=True); p.add_argument('--kind', choices=['quality','decision'], required=True)
    p.add_argument('--json', required=True)
    p.add_argument('--no-render', action='store_true', help='Defer report/hash sweep until render')
    p = sub.add_parser('add', help='Copy/register one supporting file and refresh report')
    p.add_argument('--run', required=True); p.add_argument('--file', required=True)
    p.add_argument('--role', choices=['preview','table','figure','annotation','provenance','r_script','analysis_script','guide'], required=True)
    p.add_argument('--caption', required=True); p.add_argument('--stage'); p.add_argument('--image-id')
    p.add_argument('--category'); p.add_argument('--graph-id')
    p.add_argument('--uses', action='append', help='Run-relative registered input/script path; repeatable')
    p.add_argument('--no-render', action='store_true', help='Defer report/hash sweep until render')
    p.add_argument('--scaling'); p.add_argument('--primary', action='store_true')
    p = sub.add_parser('render', help='Refresh report and CSV logs from current records')
    p.add_argument('--run', required=True)
    args = parser.parse_args()
    if args.action == 'init':
        result = init(args)
    else:
        root = Path(args.run).expanduser().resolve(strict=True)
        read(record_dir(root)/'brief.json')
        result = render(root) if args.action=='render' else (event(args,root) if args.action=='event' else add(args,root))
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, KeyError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)

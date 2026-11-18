"""Create a project README without overwriting an existing project."""
import argparse
from pathlib import Path
import re


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('name')
    args = parser.parse_args()
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,47}', args.name) or args.name in ('alerts', 'summary', 'status'):
        parser.error('Use a non-reserved lowercase project name with digits/hyphens.')
    folder = Path(__file__).resolve().parents[1] / 'projects' / args.name
    if folder.exists():
        parser.error('That project folder already exists; nothing was changed.')
    folder.mkdir(parents=True)
    (folder / 'README.md').write_text(f'# {args.name}\n\nDescribe your experiment, board, sensors and results here.\n\n'
        f'MQTT topic: `lab/{args.name}/<device>/<sensor>`.\n\n'
        'Open http://localhost:8080/new to generate your board checklist.\n'
        'Never put WiFi settings or other credentials in this folder.\n', encoding='utf-8')
    print('Created projects/' + args.name + '/README.md')


if __name__ == '__main__':
    main()

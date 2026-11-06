import math
import re

KEYS = {f'Key{chr(c)}': c for c in range(65, 91)}
KEYS.update({f'Digit{i}': 48 + i for i in range(10)})
KEYS.update({'Enter': 13, 'Tab': 9, 'Backspace': 8, 'Escape': 27, 'Space': 32,
             'ShiftLeft': 160, 'ShiftRight': 161, 'ControlLeft': 162, 'ControlRight': 163,
             'AltLeft': 164, 'AltRight': 165, 'ArrowLeft': 37, 'ArrowUp': 38,
             'ArrowRight': 39, 'ArrowDown': 40, 'Delete': 46, 'Home': 36, 'End': 35,
             'PageUp': 33, 'PageDown': 34, 'Insert': 45,
             'Minus': 189, 'Equal': 187, 'BracketLeft': 219, 'BracketRight': 221,
             'Backslash': 220, 'Semicolon': 186, 'Quote': 222, 'Comma': 188,
             'Period': 190, 'Slash': 191, 'Backquote': 192})
KEYS.update({f'F{i}': 111 + i for i in range(1, 13)})


def validate_id(value):
    if not isinstance(value, str) or not re.fullmatch(r'[0-9 ]{6,24}', value):
        raise ValueError('Informe um ID AnyDesk numérico.')
    value = value.replace(' ', '')
    if not re.fullmatch(r'[0-9]{6,12}', value):
        raise ValueError('ID AnyDesk inválido.')
    return value


def number(value, low, high):
    if type(value) not in (int, float) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError('Coordenada ou valor inválido.')
    return value


def map_point(x, y, width, height):
    number(x, 0, 1)
    number(y, 0, 1)
    if width <= 0 or height <= 0:
        raise ValueError('Janela sem área disponível.')
    return min(int(x * width), width - 1), min(int(y * height), height - 1)


def validate_event(data):
    if not isinstance(data, dict):
        raise ValueError('Evento inválido.')
    kind = data.get('type')
    fields = {'move': {'type', 'x', 'y'}, 'button': {'type', 'x', 'y', 'button', 'down'},
              'wheel': {'type', 'x', 'y', 'delta'}, 'key': {'type', 'code', 'down'}}
    if kind not in fields or set(data) != fields[kind]:
        raise ValueError('Evento desconhecido.')
    if kind in ('move', 'button', 'wheel'):
        number(data['x'], 0, 1)
        number(data['y'], 0, 1)
    if kind in ('button', 'key') and type(data['down']) is not bool:
        raise ValueError('Estado de tecla inválido.')
    if kind == 'button' and (type(data['button']) is not int or data['button'] not in (0, 1, 2)):
        raise ValueError('Botão inválido.')
    if kind == 'key' and (not isinstance(data['code'], str) or data['code'] not in KEYS):
        raise ValueError('Tecla não suportada nesta versão.')
    if kind == 'wheel':
        number(data['delta'], -1200, 1200)
    return data

import json
from io import BytesIO
from typing import List, Tuple

from PIL import Image
from pony.orm import select

import settings
from models import Product, Section, UserState


def root_choice_handler(text: str, user_id: int) -> Tuple[str, str] or bool:
    """
    Обрабатывает запросы в корневом разделе
    :param text: текст сообщения
    :param user_id: id пользователя
    :return: текст отправляемого сообщения и JSON-строка, представляющая клавиатуру,
    или False в случае некорректного запроса
    """
    sections = select(s.name for s in Section)[:]
    for section in sections:
        if section.lower() in text.lower():
            keyboard = json.dumps(get_keyboard(section))
            text_to_send = f'Вы перешли в раздел "{section}". Выберите интересующий вас товар.'
            UserState.set_current_section(user_id, section)
            return text_to_send, keyboard
    else:
        return False


def section_choice_handler(text: str, current_section: str) -> Tuple[str, BytesIO] or bool:
    """
    Обрабатывает запросы в конкретном разделе
    :param text: текст сообщения
    :param current_section: название раздела
    :return: текст отправляемого сообщения и файловый объект картинки,
    или False в случае некорректного запроса
    """
    products = select(p.name for p in Product if p.section.name == current_section)
    for product in products:
        if product.lower() in text.lower():
            product_obj = Product.get(name=product)
            image = open_image(product_obj.image)
            return product_obj.description, image
    else:
        return False


def intents_handler(text: str, user_id: int) -> Tuple[str, str] or bool:
    """
    Обрабатывает общие запросы
    :param text: текст сообщения
    :param user_id: id пользователя
    :return: текст отправляемого сообщения и JSON-строка, представляющая клавиатуру,
    или False в случае некорректного запроса
    """
    for intent in settings.INTENTS:
        if any(token in text.lower() for token in intent['tokens']):
            keyboard = json.dumps(get_keyboard(intent['section']))
            text_to_send = intent['answer']
            UserState.set_current_section(user_id, intent['section'])
            return text_to_send, keyboard
    else:
        return False


def get_keyboard(section: str = 'root') -> dict:
    """
    Возвращает клавиатуру соответственно текущему разделу
    :param section: название раздела
    :return: словарь, представляющий клавиатуру
    """
    keyboard = {
        "one_time": False,
        "buttons": [],
    }
    buttons = get_buttons_for_section(section)
    if section == 'root':
        for section_name in buttons:
            section_button = {
                "action": {
                    "type": "text",
                    "payload": "{\"button\": \"1\"}"
                }
            }
            section_button['action']['label'] = section_name
            keyboard['buttons'].append([section_button])
    else:
        back_button = {
            "action": {
                "type": "text",
                "label": "Выйти из раздела",
                "payload": "{\"button\": \"1\"}"
            },
            "color": "primary",
        }
        keyboard['buttons'].append([back_button])
        for product_name in buttons:
            product_button = {
                "action": {
                    "type": "text",
                    "payload": "{\"button\": \"1\"}"
                }
            }
            product_button['action']['label'] = product_name
            keyboard['buttons'].append([product_button])
    return keyboard


def get_buttons_for_section(section: str) -> List[str]:
    """
    Возвращает кнопки клавиатуры соответственно текущему разделу
    :param section: название раздела
    :return: список названий кнопок
    """
    if section == 'root':
        return select(s.name for s in Section)[:]
    else:
        return select(p.name for p in Product if p.section.name == section)


def open_image(image_path: str) -> BytesIO:
    """
    Подготовка картинки к использованию
    :param image_path: относительный путь к картинке
    :return: файловый объект
    """
    base = Image.open(image_path)
    temp_file = BytesIO()
    base.save(temp_file, 'png')
    temp_file.seek(0)
    return temp_file

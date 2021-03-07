import json
import logging
from random import randint
from typing import List

from pony.orm import select, db_session
from vk_api import VkApi
from vk_api.bot_longpoll import VkBotEventType, VkBotLongPoll

import settings
from models import Product, Section

log = logging.getLogger('bot')


def configure_logging():
    """Настройка логгирования"""
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(logging.Formatter('%(levelname)s %(message)s'))
    stream_handler.setLevel(logging.INFO)
    log.addHandler(stream_handler)

    file_handler = logging.FileHandler('bot.log')
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s %(message)s', '%Y-%m-%d %H:%M'))
    file_handler.setLevel(logging.DEBUG)
    log.addHandler(file_handler)

    log.setLevel(logging.DEBUG)


class UserState:
    def __init__(self, user_id):
        self.user_id = user_id
        self.section = 'root'


class Bot:
    """
    Бот vk.com для просмотра ассортимента кондитерской лавки.
    """
    def __init__(self, group_id: int, token: str):
        """
        :param group_id: group id из группы VK
        :param token: секретный токен
        """
        self.group_id = group_id
        self.token = token
        self.vk = VkApi(token=token)
        self.long_poller = VkBotLongPoll(self.vk, self.group_id)
        self.api = self.vk.get_api()
        self.user_states = {}

    def run(self):
        """Запуск бота"""
        for event in self.long_poller.listen():
            try:
                self.on_event(event)
            except Exception:
                log.exception('Ошибка в обработке события')

    @db_session
    def on_event(self, event):
        """
        Обрабатывает введенные данные
        :param event: VkBotMessageEvent object
        """
        if event.type == VkBotEventType.MESSAGE_NEW:
            user_id = event.object.message['peer_id']
            current_section = self.get_current_section(user_id)
            text = event.object.message['text']
            self.check_choice(user_id, current_section, text)
        else:
            log.debug(event.type)
            return

    def get_current_section(self, user_id):
        if user_id not in self.user_states:
            self.user_states[user_id] = 'root'
        return self.user_states[user_id]

    def get_keyboard(self, section: str = 'root') -> dict:
        """
        Возвращает клавиатуру к переданному разделу
        :param section: название раздела
        :return: словарь, представляющий клавиатуру
        """
        keyboard = {
            "one_time": False,
            "buttons": [],
        }
        buttons = self.get_buttons_for_section(section)
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

    @staticmethod
    def get_buttons_for_section(section: str) -> List[str]:
        if section == 'root':
            return select(s.name for s in Section)[:]
        else:
            return select(p.name for p in Product if p.section.name == section)

    def check_choice(self, user_id, current_section, text):
        if current_section == 'root':
            sections = select(s.name for s in Section)[:]
            for section in sections:
                if section.lower() in text.lower():
                    keyboard = json.dumps(self.get_keyboard(section))
                    text = f'Вы перешли в раздел "{section}". Выберите интересующий вас товар.'
                    self.user_states[user_id] = section
                    self.send_text(text, user_id, keyboard)
                    return
        else:
            products = select(p.name for p in Product if p.section.name == current_section)
            for product in products:
                if product.lower() in text.lower():
                    product_obj = Product.get(name=product)
                    self.send_text(product_obj.image, user_id)
                    self.send_text(product_obj.description, user_id)
                    return
        self.check_intents(user_id, text)

    def check_intents(self, user_id, text):
        """Проверка возможных запросов"""
        for intent in settings.INTENTS:
            if any(token in text.lower() for token in intent['tokens']):
                keyboard = json.dumps(self.get_keyboard(intent['section']))
                self.user_states[user_id] = intent['section']
                self.send_text(intent['answer'], user_id, keyboard)
                break
        else:
            keyboard = json.dumps(self.get_keyboard('root'))
            self.user_states[user_id] = 'root'
            self.send_text(settings.DEFAULT_ANSWER, user_id, keyboard)

    def send_text(self, text_to_send, user_id, keyboard=None):
        """Отправка сообщения в VK"""
        self.api.messages.send(
            keyboard=keyboard,
            message=text_to_send,
            random_id=randint(0, 2 ** 20),
            peer_id=user_id
        )


if __name__ == "__main__":
    configure_logging()
    bot = Bot(settings.GROUP_ID, settings.TOKEN)
    bot.run()

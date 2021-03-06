import json
import logging
from random import randint

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

    def run(self):
        """Запуск бота"""
        for event in self.long_poller.listen():
            try:
                self.on_event(event)
            except Exception:
                log.exception('Ошибка в обработке события')

    def on_event(self, event):
        """
        Обрабатывает введенные данные
        :param event: VkBotMessageEvent object
        """
        if event.type == VkBotEventType.MESSAGE_NEW:
            user_id = event.object.message['peer_id']
            keyboard = json.dumps(self.get_keyboard('root'))

            self.api.messages.send(
                message='Выберите раздел',
                keyboard=keyboard,
                random_id=randint(0, 2 ** 20),
                peer_id=user_id
            )
        else:
            log.debug(event.type)
            return

    @db_session
    def get_keyboard(self, section: str) -> dict:
        """
        Возвращает клавиатуру к переданному разделу
        :param section: название раздела
        :return: словарь, представляющий клавиатуру
        """
        keyboard = {
            "one_time": False,
            "buttons": [],
        }
        if section == 'root':
            sections = select(s.name for s in Section)[:]
            for i, section_name in enumerate(sections):
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
            products = select(p.name for p in Product if p.section.name == section)[:]
            for i, product_name in enumerate(products):
                product_button = {
                    "action": {
                        "type": "text",
                        "payload": "{\"button\": \"1\"}"
                    }
                }
                product_button['action']['label'] = product_name
                keyboard['buttons'].append([product_button])
        return keyboard


if __name__ == "__main__":
    configure_logging()
    bot = Bot(settings.GROUP_ID, settings.TOKEN)
    bot.run()

from pony.orm import Database, db_session, Required, Set

DATABASE_DICT = {
    'Пончики': {
        'Пончики с сахарной пудрой': {
            'image': 'img/sugar_donut.jpg',
            'description': 'Свежайшие пончики с пылу с жару, посыпанные сахарной пудрой',
        },
        'Шоколадные пончики': {
            'image': 'img/chocolate_donut.jpg',
            'description': 'Ароматные пончики в шоколадной глазури',
        },
        'Клубничные пончики': {
            'image': 'img/strawberry_donut.jpg',
            'description': 'Летняя сладость с пончиками в клубничной глазури',
        },
    },
    'Кексы': {
        'Кексы с изюмом': {
            'image': 'img/raisin_muffin.jpg',
            'description': 'Кексы с изюмом, прямо как делала ваша бабушка',
        },
        'Шоколадные кексы': {
            'image': 'img/chocolate_muffin.jpg',
            'description': 'Шоколадные кексы и кофе - бессмертная классика',
        },
        'Кексы с черникой': {
            'image': 'img/blueberry_muffin.jpg',
            'description': 'Съешь быстрее, чтобы добраться до сочной черники!',
        },
    },
    'Штрудели': {
        'Яблочный штрудель': {
            'image': 'img/apple_strudel.jpg',
            'description': 'Классический немецкий рецепт яблочного штруделя, проверенный веками',
        },
        'Грушевый штрудель': {
            'image': 'img/pear_strudel.jpg',
            'description': 'Нежная фруктовая радость и сладость',
        },
        'Вишневый штрудель': {
            'image': 'img/cherry_strudel.jpg',
            'description': 'Ягодный взрыв в нежнейшем слоеном тесте',
        },
    },
}

db = Database()
db.bind(provider='sqlite', filename='sweetbot.db', create_db=True)


class Section(db.Entity):
    name = Required(str)
    products = Set('Product')


class Product(db.Entity):
    name = Required(str)
    description = Required(str)
    image = Required(str)
    section = Required(Section)


db.generate_mapping(create_tables=True)

if __name__ == '__main__':
    with db_session:
        for section_name, section_products in DATABASE_DICT.items():
            section = Section(name=section_name)
            for product, product_data in section_products.items():
                Product(
                    name=product,
                    description=product_data['description'],
                    image=product_data['image'],
                    section=section,
                )

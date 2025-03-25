import sqlalchemy as sa
import sqlalchemy.orm as orm
from sqlalchemy.orm import Session

SqlAlchemyBase = orm.declarative_base()

__factory = None
__engine = None  # Добавляем глобальную переменную для движка

def global_init(db_file):
    global __factory, __engine

    if __factory:
        return

    if not db_file or not db_file.strip():
        raise Exception("Необходимо указать файл базы данных.")

    conn_str = f'sqlite:///{db_file.strip()}?check_same_thread=False'
    print(f"Подключение к базе данных по адресу {conn_str}")

    engine = sa.create_engine(conn_str, echo=True)
    __engine = engine  # Сохраняем движок в глобальную переменную
    __factory = orm.sessionmaker(bind=engine)

    from . import __all_models

    SqlAlchemyBase.metadata.create_all(engine)

def create_session() -> Session:
    global __factory
    return __factory()

def get_engine():  # Добавляем функцию для получения движка
    global __engine
    return __engine
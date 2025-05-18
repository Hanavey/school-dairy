import logging
from aiogram import Bot, Dispatcher, Router, types
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.event import listen
from datetime import datetime
from data.db_session import global_init, create_session
from data.user import User
from data.student import Student
from data.teacher import Teacher
from data.grade import Grade
from data.attendance import Attendance
from data.schedule import Schedule
from data.homework import Homework
from data.classes import Class
from data.subject import Subject
from data.teacher_position_assignment import TeacherPositionAssignment
from data.teacher_position import TeacherPosition

logging.basicConfig(
    filename='api_access.log',
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] - %(message)s',
    encoding='utf-8'
)

API_TOKEN = "7613605004:AAEUhlZYxTWLWhJL3KHROI7afHaD8IobBZs"
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot=bot, storage=storage)
router = Router()
dp.include_router(router)

global_init("db/school_diary.db")
SessionBase = declarative_base()

class TelegramSession(SessionBase):
    __tablename__ = 'sessions'
    telegram_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    role = Column(String, nullable=False)

    def __repr__(self):
        return f"<TelegramSession(telegram_id={self.telegram_id}, user_id={self.user_id}, role={self.role})>"

def init_session_db():
    engine = create_engine("sqlite:///db/telegram_bot.db?check_same_thread=False", echo=True)
    def _fk_pragma_on_connect(dbapi_con, con_record):
        dbapi_con.execute('PRAGMA foreign_keys=ON')
    listen(engine, 'connect', _fk_pragma_on_connect)
    SessionBase.metadata.create_all(engine)
    return sessionmaker(bind=engine)

SessionSession = init_session_db()

def is_authorized(telegram_id: int) -> tuple:
    session = SessionSession()
    try:
        ts = session.query(TelegramSession).filter(TelegramSession.telegram_id == telegram_id).first()
        logging.debug(f"Checking authorization for telegram_id={telegram_id}: user_id={ts.user_id if ts else None}, role={ts.role if ts else None}")
        return (ts.user_id, ts.role) if ts else (None, None)
    except Exception as e:
        logging.error(f"Error checking authorization for telegram_id={telegram_id}: {e}")
        return (None, None)
    finally:
        session.close()

# Главное меню для роли
def get_main_menu(role: str) -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(
        keyboard=[],
        resize_keyboard=True,
        row_width=2
    )
    if role == "student":
        keyboard.keyboard = [
            [KeyboardButton(text="Оценки и посещаемость"), KeyboardButton(text="Расписание")],
            [KeyboardButton(text="Домашние задания"), KeyboardButton(text="Одноклассники")],
            [KeyboardButton(text="Выйти")]
        ]
    elif role == "teacher":
        keyboard.keyboard = [
            [KeyboardButton(text="Ведомые классы"), KeyboardButton(text="Информация о классе")],
            [KeyboardButton(text="Расписание"), KeyboardButton(text="Выйти")]
        ]
    logging.debug(f"Created main menu for role={role}: {keyboard.keyboard}")
    return keyboard

# Клавиатура для управления классом
def get_manage_class_keyboard() -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Просмотреть оценки"), KeyboardButton(text="Добавить оценку")],
            [KeyboardButton(text="Просмотреть посещаемость"), KeyboardButton(text="Добавить посещаемость")],
            [KeyboardButton(text="Добавить ДЗ"), KeyboardButton(text="Назад")]
        ],
        resize_keyboard=True,
        row_width=2
    )
    logging.debug("Created manage class keyboard")
    return keyboard

DAY_ORDER = {
    "Понедельник": 1,
    "Вторник": 2,
    "Среда": 3,
    "Четверг": 4,
    "Пятница": 5,
    "Суббота": 6,
    "Воскресенье": 7
}

# Машина состояний для аутентификации
class AuthStates(StatesGroup):
    WAITING_FOR_ROLE = State()
    WAITING_FOR_USERNAME = State()
    WAITING_FOR_PASSWORD = State()

# Машина состояний для ученика
class StudentStates(StatesGroup):
    MAIN_MENU = State()
    SELECT_SUBJECT = State()

# Машина состояний для учителя
class TeacherStates(StatesGroup):
    MAIN_MENU = State()
    SELECT_CLASS = State()
    SELECT_SUBJECT = State()
    MANAGE_CLASS = State()
    ADD_GRADE_SELECT_STUDENT = State()
    ADD_GRADE_ENTER_GRADE = State()
    ADD_GRADE_ENTER_DATE = State()
    ADD_ATTENDANCE_SELECT_STUDENT = State()
    ADD_ATTENDANCE_ENTER_STATUS = State()
    ADD_ATTENDANCE_ENTER_DATE = State()
    ADD_HOMEWORK_ENTER_TASK = State()
    ADD_HOMEWORK_ENTER_DUE_DATE = State()

# Команда /start
@router.message(CommandStart())
async def start_command(message: types.Message, state: FSMContext):
    telegram_id = message.from_user.id
    logging.debug(f"Received /start from telegram_id={telegram_id}")
    user_id, role = is_authorized(telegram_id)

    if user_id:
        keyboard = get_main_menu(role)
        if role == "student":
            await state.set_state(StudentStates.MAIN_MENU)
            logging.debug(f"Set state to StudentStates.MAIN_MENU for telegram_id={telegram_id}")
            await message.answer("Вы вошли как ученик.", reply_markup=keyboard)
        elif role == "teacher":
            await state.set_state(TeacherStates.MAIN_MENU)
            logging.debug(f"Set state to TeacherStates.MAIN_MENU for telegram_id={telegram_id}")
            await message.answer("Вы вошли как учитель.", reply_markup=keyboard)
    else:
        keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="Ученик"), KeyboardButton(text="Учитель")]
            ],
            resize_keyboard=True,
            row_width=2
        )
        await state.set_state(AuthStates.WAITING_FOR_ROLE)
        logging.debug(f"Set state to AuthStates.WAITING_FOR_ROLE for telegram_id={telegram_id}")
        await message.answer("Выберите вашу роль:", reply_markup=keyboard)

# Выбор роли
@router.message(AuthStates.WAITING_FOR_ROLE, lambda message: message.text.strip() in ["Ученик", "Учитель"])
async def process_role(message: types.Message, state: FSMContext):
    role = message.text.strip()
    logging.debug(f"Selected role: {role}")
    await state.update_data(role=role)
    await state.set_state(AuthStates.WAITING_FOR_USERNAME)
    await message.answer("Введите ваш логин:", reply_markup=types.ReplyKeyboardRemove())

@router.message(AuthStates.WAITING_FOR_ROLE)
async def process_invalid_role(message: types.Message):
    logging.debug(f"Invalid role selected: '{message.text}'")
    await message.answer("Пожалуйста, выберите 'Ученик' или 'Учитель'.")

# Ввод логина
@router.message(AuthStates.WAITING_FOR_USERNAME)
async def process_username(message: types.Message, state: FSMContext):
    username = message.text.strip()
    logging.debug(f"Received username: {username}")
    await state.update_data(username=username)
    await state.set_state(AuthStates.WAITING_FOR_PASSWORD)
    await message.answer("Введите ваш пароль:")

# Ввод пароля и проверка
@router.message(AuthStates.WAITING_FOR_PASSWORD)
async def process_password(message: types.Message, state: FSMContext):
    data = await state.get_data()
    username = data["username"]
    role = data["role"]
    password = message.text
    telegram_id = message.from_user.id
    logging.debug(f"Processing password for username={username}, role={role}")

    session = create_session()
    try:
        user = session.query(User).filter(User.username == username).first()
        if not user or not user.check_password(password):
            logging.warning(f"Invalid login or password for username={username}")
            await message.answer("Неверный логин или пароль.")
            await state.set_data({})
            await start_command(message, state)
            return

        if role == "Ученик":
            student = session.query(Student).filter(Student.user_id == user.user_id).first()
            if not student:
                logging.warning(f"User {username} is not a student")
                await message.answer("Вы не зарегистрированы как ученик.")
                await state.set_data({})
                await start_command(message, state)
                return
            role_db = "student"
        elif role == "Учитель":
            teacher = session.query(Teacher).filter(Teacher.user_id == user.user_id).first()
            if not teacher:
                logging.warning(f"User {username} is not a teacher")
                await message.answer("Вы не зарегистрированы как учитель.")
                await state.set_data({})
                await start_command(message, state)
                return
            role_db = "teacher"

        session_session = SessionSession()
        try:
            ts = session_session.query(TelegramSession).filter(TelegramSession.telegram_id == telegram_id).first()
            if ts:
                ts.user_id = user.user_id
                ts.role = role_db
            else:
                ts = TelegramSession(telegram_id=telegram_id, user_id=user.user_id, role=role_db)
                session_session.add(ts)
            session_session.commit()
            logging.debug(f"Saved session for telegram_id={telegram_id}, user_id={user.user_id}, role={role_db}")
        except Exception as e:
            logging.error(f"Error saving session for telegram_id={telegram_id}: {e}")
            await message.answer("Ошибка при сохранении сессии. Попробуйте снова.")
            await state.set_data({})
            await start_command(message, state)
            return
        finally:
            session_session.close()

        keyboard = get_main_menu(role_db)
        if role_db == "student":
            await state.set_state(StudentStates.MAIN_MENU)
            logging.debug(f"Set state to StudentStates.MAIN_MENU for telegram_id={telegram_id}")
            await message.answer("Вы вошли как ученик.", reply_markup=keyboard)
        elif role_db == "teacher":
            await state.set_state(TeacherStates.MAIN_MENU)
            logging.debug(f"Set state to TeacherStates.MAIN_MENU for telegram_id={telegram_id}")
            await message.answer("Вы вошли как учитель.", reply_markup=keyboard)
    except Exception as e:
        logging.error(f"Error processing password for telegram_id={telegram_id}: {e}")
        await message.answer("Произошла ошибка. Попробуйте снова.")
        await state.set_data({})
    finally:
        session.close()

# Выход из аккаунта
@router.message(lambda message: message.text.strip() == "Выйти")
async def logout(message: types.Message, state: FSMContext):
    telegram_id = message.from_user.id
    logging.debug(f"Logging out telegram_id={telegram_id}")
    session = SessionSession()
    try:
        ts = session.query(TelegramSession).filter(TelegramSession.telegram_id == telegram_id).first()
        if ts:
            session.delete(ts)
            session.commit()
            logging.debug(f"Session deleted for telegram_id={telegram_id}")
        await message.answer("Вы вышли из аккаунта.")
    except Exception as e:
        logging.error(f"Error during logout for telegram_id={telegram_id}: {e}")
        await message.answer("Ошибка при выходе. Попробуйте снова.")
    finally:
        session.close()

    await state.set_data({})
    await start_command(message, state)

# --- Функционал ученика ---
@router.message(StudentStates.MAIN_MENU, lambda message: message.text.strip() == "Оценки и посещаемость")
async def student_grades_attendance(message: types.Message, state: FSMContext):
    telegram_id = message.from_user.id
    current_state = await state.get_state()
    logging.debug(f"Student grades and attendance requested by telegram_id={telegram_id}, state={current_state}")
    user_id, role = is_authorized(telegram_id)
    if not user_id or role != "student":
        logging.warning(f"Unauthorized access attempt by telegram_id={telegram_id}")
        await message.answer("Пожалуйста, войдите в аккаунт.")
        await state.set_data({})
        await start_command(message, state)
        return

    session = create_session()
    try:
        student = session.query(Student).filter(Student.user_id == user_id).first()
        if not student:
            logging.warning(f"No student found for user_id={user_id}")
            await message.answer("Данные ученика не найдены.")
            await state.set_data({})
            await start_command(message, state)
            return

        subjects = session.query(Subject).all()
        if not subjects:
            logging.debug(f"No subjects found for telegram_id={telegram_id}")
            await message.answer("Предметы не найдены.")
            return

        keyboard = InlineKeyboardMarkup(inline_keyboard=[], row_width=1)
        for subject in subjects:
            keyboard.inline_keyboard.append(
                [InlineKeyboardButton(text=subject.subject_name, callback_data=f"subject_{subject.subject_id}")]
            )

        await state.set_state(StudentStates.SELECT_SUBJECT)
        logging.debug(f"Set state to StudentStates.SELECT_SUBJECT for telegram_id={telegram_id}")
        try:
            await message.delete()
        except Exception as e:
            logging.warning(f"Failed to delete message for telegram_id={telegram_id}: {e}")
        await message.answer("Выберите предмет:", reply_markup=keyboard)
    except Exception as e:
        logging.error(f"Error in student_grades_attendance for telegram_id={telegram_id}: {e}")
        await message.answer("Произошла ошибка. Попробуйте снова.")
        await state.set_state(StudentStates.MAIN_MENU)
        await state.set_data({})
    finally:
        session.close()

@router.callback_query(StudentStates.SELECT_SUBJECT, lambda c: c.data.startswith("subject_"))
async def process_subject_selection(callback_query: types.CallbackQuery, state: FSMContext):
    try:
        subject_id = int(callback_query.data.split("_")[1])
        telegram_id = callback_query.from_user.id
        logging.debug(f"Subject selected: subject_id={subject_id} by telegram_id={telegram_id}")
        user_id, role = is_authorized(telegram_id)
        if not user_id or role != "student":
            logging.warning(f"Unauthorized access attempt by telegram_id={telegram_id}")
            await callback_query.message.answer("Пожалуйста, войдите в аккаунт.")
            await state.set_data({})
            await callback_query.message.answer("Выберите роль:", reply_markup=get_main_menu(None))
            await callback_query.answer()
            return

        session = create_session()
        try:
            student = session.query(Student).filter(Student.user_id == user_id).first()
            if not student:
                logging.warning(f"No student found for user_id={user_id}")
                await callback_query.message.answer("Данные ученика не найдены.")
                await state.set_data({})
                await callback_query.message.answer("Выберите роль:", reply_markup=get_main_menu(None))
                await callback_query.answer()
                return

            grades = session.query(Grade).filter(Grade.student_id == student.user_id, Grade.subject_id == subject_id).all()
            attendance = session.query(Attendance).filter(Attendance.student_id == student.user_id).all()

            response = f"Оценки по предмету:\n"
            if grades:
                for grade in grades:
                    response += f"{grade.date}: {grade.grade}\n"
            else:
                response += "Оценки отсутствуют.\n"

            response += "\nПосещаемость:\n"
            if attendance:
                for att in attendance:
                    response += f"{att.date}: {att.status}\n"
            else:
                response += "Записи о посещаемости отсутствуют.\n"

            try:
                await callback_query.message.delete()
            except Exception as e:
                logging.warning(f"Failed to delete message for telegram_id={telegram_id}: {e}")
            await callback_query.message.answer(response)
            await state.set_state(StudentStates.MAIN_MENU)
            await state.set_data({})
            logging.debug(f"Set state to StudentStates.MAIN_MENU for telegram_id={telegram_id}")
            await callback_query.message.answer("Вернуться в меню:", reply_markup=get_main_menu("student"))
            await callback_query.answer()
        except Exception as e:
            logging.error(f"Error in process_subject_selection for telegram_id={telegram_id}: {e}")
            await callback_query.message.answer("Произошла ошибка. Попробуйте снова.")
            await state.set_state(StudentStates.MAIN_MENU)
            await state.set_data({})
            await callback_query.answer()
        finally:
            session.close()
    except Exception as e:
        logging.error(f"Callback error in process_subject_selection for telegram_id={telegram_id}: {e}")
        await callback_query.message.answer("Ошибка обработки. Попробуйте снова.")
        await state.set_state(StudentStates.MAIN_MENU)
        await state.set_data({})
        await callback_query.answer()

@router.message(StudentStates.MAIN_MENU, lambda message: message.text.strip() == "Расписание")
async def student_schedule(message: types.Message, state: FSMContext):
    telegram_id = message.from_user.id
    current_state = await state.get_state()
    logging.debug(f"Student schedule requested by telegram_id={telegram_id}, state={current_state}")
    user_id, role = is_authorized(telegram_id)
    if not user_id or role != "student":
        logging.warning(f"Unauthorized access attempt by telegram_id={telegram_id}")
        await message.answer("Пожалуйста, войдите в аккаунт.")
        await state.set_data({})
        await start_command(message, state)
        return

    session = create_session()
    try:
        student = session.query(Student).filter(Student.user_id == user_id).first()
        if not student:
            logging.warning(f"No student found for user_id={user_id}")
            await message.answer("Данные ученика не найдены.")
            await state.set_data({})
            await start_command(message, state)
            return

        schedules = session.query(Schedule).filter(Schedule.class_id == student.class_id).all()
        if not schedules:
            logging.debug(f"No schedules found for class_id={student.class_id}")
            await message.answer("Расписание не найдено.")
            return

        schedules = sorted(
            schedules,
            key=lambda sch: (DAY_ORDER.get(sch.day_of_week, 8), sch.start_time)
        )

        response = "Расписание:\n"
        for sch in schedules:
            subject = session.query(Subject).filter(Subject.subject_id == sch.subject_id).first()
            response += f"{sch.day_of_week} {sch.start_time}-{sch.end_time}: {subject.subject_name if subject else 'Неизвестный предмет'}\n"

        try:
            await message.delete()
        except Exception as e:
            logging.warning(f"Failed to delete message for telegram_id={telegram_id}: {e}")
        await message.answer(response, reply_markup=get_main_menu("student"))
        await state.set_state(StudentStates.MAIN_MENU)
        await state.set_data({})
    except Exception as e:
        logging.error(f"Error in student_schedule for telegram_id={telegram_id}: {e}")
        await message.answer("Произошла ошибка. Попробуйте снова.")
        await state.set_state(StudentStates.MAIN_MENU)
        await state.set_data({})
    finally:
        session.close()

@router.message(StudentStates.MAIN_MENU, lambda message: message.text.strip() == "Домашние задания")
async def student_homework(message: types.Message, state: FSMContext):
    telegram_id = message.from_user.id
    current_state = await state.get_state()
    logging.debug(f"Student homework requested by telegram_id={telegram_id}, state={current_state}")
    user_id, role = is_authorized(telegram_id)
    if not user_id or role != "student":
        logging.warning(f"Unauthorized access attempt by telegram_id={telegram_id}")
        await message.answer("Пожалуйста, войдите в аккаунт.")
        await state.set_data({})
        await start_command(message, state)
        return

    session = create_session()
    try:
        student = session.query(Student).filter(Student.user_id == user_id).first()
        if not student:
            logging.warning(f"No student found for user_id={user_id}")
            await message.answer("Данные ученика не найдены.")
            await state.set_data({})
            await start_command(message, state)
            return

        homeworks = session.query(Homework).filter(Homework.class_id == student.class_id).all()
        if not homeworks:
            logging.debug(f"No homeworks found for class_id={student.class_id}")
            await message.answer("Домашние задания не найдены.")
            return

        response = "Домашние задания:\n"
        for hw in homeworks:
            subject = session.query(Subject).filter(Subject.subject_id == hw.subject_id).first()
            response += f"{subject.subject_name if subject else 'Неизвестный предмет'} (к {hw.due_date}): {hw.task}\n"

        try:
            await message.delete()
        except Exception as e:
            logging.warning(f"Failed to delete message for telegram_id={telegram_id}: {e}")
        await message.answer(response, reply_markup=get_main_menu("student"))
        await state.set_state(StudentStates.MAIN_MENU)
        await state.set_data({})
    except Exception as e:
        logging.error(f"Error in student_homework for telegram_id={telegram_id}: {e}")
        await message.answer("Произошла ошибка. Попробуйте снова.")
        await state.set_state(StudentStates.MAIN_MENU)
        await state.set_data({})
    finally:
        session.close()

@router.message(StudentStates.MAIN_MENU, lambda message: message.text.strip() == "Одноклассники")
async def student_classmates(message: types.Message, state: FSMContext):
    telegram_id = message.from_user.id
    current_state = await state.get_state()
    logging.debug(f"Student classmates requested by telegram_id={telegram_id}, state={current_state}")
    user_id, role = is_authorized(telegram_id)
    if not user_id or role != "student":
        logging.warning(f"Unauthorized access attempt by telegram_id={telegram_id}")
        await message.answer("Пожалуйста, войдите в аккаунт.")
        await state.set_data({})
        await start_command(message, state)
        return

    session = create_session()
    try:
        student = session.query(Student).filter(Student.user_id == user_id).first()
        if not student:
            logging.warning(f"No student found for user_id={user_id}")
            await message.answer("Данные ученика не найдены.")
            await state.set_data({})
            await start_command(message, state)
            return

        classmates = session.query(Student).filter(Student.class_id == student.class_id).all()
        if not classmates:
            logging.debug(f"No classmates found for class_id={student.class_id}")
            await message.answer("Одноклассники не найдены.")
            return

        response = "Одноклассники:\n"
        for cm in classmates:
            user = session.query(User).filter(User.user_id == cm.user_id).first()
            response += f"{user.first_name} {user.last_name}, {user.phone_number or 'Нет номера'}, {user.email or 'Нет email'}\n"

        try:
            await message.delete()
        except Exception as e:
            logging.warning(f"Failed to delete message for telegram_id={telegram_id}: {e}")
        await message.answer(response, reply_markup=get_main_menu("student"))
        await state.set_state(StudentStates.MAIN_MENU)
        await state.set_data({})
    except Exception as e:
        logging.error(f"Error in student_classmates for telegram_id={telegram_id}: {e}")
        await message.answer("Произошла ошибка. Попробуйте снова.")
        await state.set_state(StudentStates.MAIN_MENU)
        await state.set_data({})
    finally:
        session.close()

# --- Функционал учителя ---
@router.message(TeacherStates.MAIN_MENU, lambda message: message.text.strip() == "Ведомые классы")
async def teacher_classes(message: types.Message, state: FSMContext):
    telegram_id = message.from_user.id
    current_state = await state.get_state()
    logging.debug(f"Teacher classes requested by telegram_id={telegram_id}, state={current_state}")
    user_id, role = is_authorized(telegram_id)
    if not user_id or role != "teacher":
        logging.warning(f"Unauthorized access attempt by telegram_id={telegram_id}")
        await message.answer("Пожалуйста, войдите в аккаунт.")
        await state.set_data({})
        await start_command(message, state)
        return

    session = create_session()
    try:
        teacher = session.query(Teacher).filter(Teacher.user_id == user_id).first()
        if not teacher:
            logging.warning(f"No teacher found for user_id={user_id}")
            await message.answer("Данные учителя не найдены.")
            await state.set_data({})
            await start_command(message, state)
            return

        position_assignment = session.query(TeacherPositionAssignment).filter(
            TeacherPositionAssignment.teacher_id == teacher.teacher_id
        ).first()
        if not position_assignment:
            logging.warning(f"No position found for teacher_id={teacher.teacher_id}")
            await message.answer("Роль учителя не определена.")
            await state.set_state(TeacherStates.MAIN_MENU)
            await state.set_data({})
            return

        position = session.query(TeacherPosition).filter(
            TeacherPosition.position_id == position_assignment.position_id
        ).first()
        is_deputy = position and position.position_name == "Завуч"
        logging.debug(f"Teacher telegram_id={telegram_id}, position={position.position_name if position else 'None'}, is_deputy={is_deputy}")

        if is_deputy:
            classes = session.query(Class).all()
        else:
            classes = session.query(Class).join(Schedule).filter(
                Schedule.teacher_id == teacher.teacher_id
            ).distinct().all()

        if not classes:
            logging.debug(f"No classes found for teacher_id={teacher.teacher_id}, is_deputy={is_deputy}")
            await message.answer("Ведомые классы не найдены.")
            await state.set_state(TeacherStates.MAIN_MENU)
            await state.set_data({})
            return

        keyboard = InlineKeyboardMarkup(inline_keyboard=[], row_width=1)
        for cls in classes:
            keyboard.inline_keyboard.append(
                [InlineKeyboardButton(text=cls.class_name, callback_data=f"class_{cls.class_id}")]
            )

        await state.set_state(TeacherStates.SELECT_CLASS)
        await state.set_data({})
        logging.debug(f"Set state to TeacherStates.SELECT_CLASS for telegram_id={telegram_id}")
        try:
            await message.delete()
        except Exception as e:
            logging.warning(f"Failed to delete message for telegram_id={telegram_id}: {e}")
        await message.answer("Выберите класс:", reply_markup=keyboard)
    except Exception as e:
        import traceback
        logging.error(f"Error in teacher_classes for telegram_id={telegram_id}: {e}\n{traceback.format_exc()}")
        await message.answer("Произошла ошибка. Попробуйте снова.")
        await state.set_state(TeacherStates.MAIN_MENU)
        await state.set_data({})
    finally:
        session.close()

@router.callback_query(TeacherStates.SELECT_CLASS, lambda c: c.data.startswith("class_"))
async def process_class_selection(callback_query: types.CallbackQuery, state: FSMContext):
    try:
        class_id = int(callback_query.data.split("_")[1])
        telegram_id = callback_query.from_user.id
        logging.debug(f"Class selected: class_id={class_id} by telegram_id={telegram_id}")
        user_id, role = is_authorized(telegram_id)
        if not user_id or role != "teacher":
            logging.warning(f"Unauthorized access attempt by telegram_id={telegram_id}")
            await callback_query.message.answer("Пожалуйста, войдите в аккаунт.")
            await state.set_data({})
            await callback_query.message.answer("Выберите роль:", reply_markup=get_main_menu(None))
            await callback_query.answer()
            return

        session = create_session()
        try:
            teacher = session.query(Teacher).filter(Teacher.user_id == user_id).first()
            if not teacher:
                logging.warning(f"No teacher found for user_id={user_id}")
                await callback_query.message.answer("Данные учителя не найдены.")
                await state.set_data({})
                await callback_query.message.answer("Выберите роль:", reply_markup=get_main_menu(None))
                await callback_query.answer()
                return

            position_assignment = session.query(TeacherPositionAssignment).filter(
                TeacherPositionAssignment.teacher_id == teacher.teacher_id
            ).first()
            if not position_assignment:
                logging.warning(f"No position found for teacher_id={teacher.teacher_id}")
                await callback_query.message.answer("Роль учителя не определена.")
                await state.set_state(TeacherStates.MAIN_MENU)
                await state.set_data({})
                await callback_query.message.answer("Вернуться в меню:", reply_markup=get_main_menu("teacher"))
                await callback_query.answer()
                return

            position = session.query(TeacherPosition).filter(
                TeacherPosition.position_id == position_assignment.position_id
            ).first()
            is_deputy = position and position.position_name == "Завуч"
            logging.debug(f"Teacher telegram_id={telegram_id}, position={position.position_name if position else 'None'}, is_deputy={is_deputy}")

            if is_deputy:
                logging.debug(f"Fetching all subjects for class_id={class_id} (deputy)")
                subjects = session.query(Subject).join(Schedule).filter(
                    Schedule.class_id == class_id
                ).distinct().all()
                schedule_entries = session.query(Schedule, Subject).join(Subject).filter(
                    Schedule.class_id == class_id
                ).all()
                logging.debug(f"Schedule entries for class_id={class_id}: " +
                            f"[{', '.join(f'{sub.subject_name} (teacher_id={sch.teacher_id})' for sch, sub in schedule_entries)}]")
            else:
                logging.debug(f"Fetching subjects for class_id={class_id}, teacher_id={teacher.teacher_id} (non-deputy)")
                subjects = session.query(Subject).join(Schedule).filter(
                    Schedule.class_id == class_id,
                    Schedule.teacher_id == teacher.teacher_id
                ).distinct().all()
                schedule_entries = session.query(Schedule, Subject).join(Subject).filter(
                    Schedule.class_id == class_id,
                    Schedule.teacher_id == teacher.teacher_id
                ).all()
                logging.debug(f"Schedule entries for class_id={class_id}, teacher_id={teacher.teacher_id}: " +
                            f"[{', '.join(f'{sub.subject_name} (teacher_id={sch.teacher_id})' for sch, sub in schedule_entries)}]")

            if not subjects:
                logging.debug(f"No subjects found for class_id={class_id}, teacher_id={teacher.teacher_id}, is_deputy={is_deputy}")
                await callback_query.message.answer("Предметы не найдены.")
                await state.set_state(TeacherStates.MAIN_MENU)
                await state.set_data({})
                await callback_query.message.answer("Вернуться в меню:", reply_markup=get_main_menu("teacher"))
                await callback_query.answer()
                return

            logging.debug(f"Found subjects for class_id={class_id}, is_deputy={is_deputy}: {[s.subject_name for s in subjects]}")
            keyboard = InlineKeyboardMarkup(inline_keyboard=[], row_width=1)
            for subject in subjects:
                keyboard.inline_keyboard.append(
                    [InlineKeyboardButton(text=subject.subject_name, callback_data=f"subject_{subject.subject_id}_{class_id}")]
                )

            await state.set_state(TeacherStates.SELECT_SUBJECT)
            await state.update_data(class_id=class_id)
            logging.debug(f"Set state to TeacherStates.SELECT_SUBJECT for telegram_id={telegram_id}")
            try:
                await callback_query.message.delete()
            except Exception as e:
                logging.warning(f"Failed to delete message for telegram_id={telegram_id}: {e}")
            await callback_query.message.answer("Выберите предмет:", reply_markup=keyboard)
            await callback_query.answer()
        except Exception as e:
            logging.error(f"Error in process_class_selection for telegram_id={telegram_id}: {e}")
            await callback_query.message.answer("Произошла ошибка. Попробуйте снова.")
            await state.set_state(TeacherStates.MAIN_MENU)
            await state.set_data({})
            await callback_query.answer()
        finally:
            session.close()
    except Exception as e:
        logging.error(f"Callback error in process_class_selection for telegram_id={telegram_id}: {e}")
        await callback_query.message.answer("Ошибка обработки. Попробуйте снова.")
        await state.set_state(TeacherStates.MAIN_MENU)
        await state.set_data({})
        await callback_query.answer()

@router.callback_query(TeacherStates.SELECT_SUBJECT, lambda c: c.data.startswith("subject_"))
async def process_teacher_subject(callback_query: types.CallbackQuery, state: FSMContext):
    try:
        data = callback_query.data.split("_")
        subject_id, class_id = int(data[1]), int(data[2])
        telegram_id = callback_query.from_user.id
        logging.debug(f"Subject selected: subject_id={subject_id}, class_id={class_id} by telegram_id={telegram_id}")

        await state.set_state(TeacherStates.MANAGE_CLASS)
        await state.update_data(subject_id=subject_id, class_id=class_id)
        logging.debug(f"Set state to TeacherStates.MANAGE_CLASS for telegram_id={telegram_id}")
        try:
            await callback_query.message.delete()
        except Exception as e:
            logging.warning(f"Failed to delete message for telegram_id={telegram_id}: {e}")
        await callback_query.message.answer("Выберите действие:", reply_markup=get_manage_class_keyboard())
        await callback_query.answer()
    except Exception as e:
        logging.error(f"Callback error in process_teacher_subject for telegram_id={telegram_id}: {e}")
        await callback_query.message.answer("Ошибка обработки. Попробуйте снова.", reply_markup=get_main_menu("teacher"))
        await state.set_state(TeacherStates.MAIN_MENU)
        await state.set_data({})
        await callback_query.answer()

@router.message(TeacherStates.MANAGE_CLASS, lambda message: message.text.strip() == "Просмотреть оценки")
async def teacher_view_grades(message: types.Message, state: FSMContext):
    data = await state.get_data()
    subject_id, class_id = data.get("subject_id"), data.get("class_id")
    telegram_id = message.from_user.id
    current_state = await state.get_state()
    logging.debug(f"Teacher grades requested: subject_id={subject_id}, class_id={class_id} by telegram_id={telegram_id}, state={current_state}")

    session = create_session()
    try:
        grades = session.query(Grade).join(Student).filter(Grade.subject_id == subject_id, Student.class_id == class_id).all()
        if not grades:
            logging.debug(f"No grades found for subject_id={subject_id}, class_id={class_id}")
            await message.answer("Оценки не найдены.", reply_markup=get_manage_class_keyboard())
            return

        response = "Оценки:\n"
        for grade in grades:
            student = session.query(Student).filter(Student.user_id == grade.student_id).first()
            user = session.query(User).filter(User.user_id == student.user_id).first()
            response += f"{user.first_name} {user.last_name} - {grade.date}: {grade.grade}\n"

        try:
            await message.delete()
        except Exception as e:
            logging.warning(f"Failed to delete message for telegram_id={telegram_id}: {e}")
        await message.answer(response, reply_markup=get_manage_class_keyboard())
        await state.set_state(TeacherStates.MANAGE_CLASS)
    except Exception as e:
        logging.error(f"Error in teacher_view_grades for telegram_id={telegram_id}: {e}")
        await message.answer("Произошла ошибка. Попробуйте снова.", reply_markup=get_manage_class_keyboard())
        await state.set_state(TeacherStates.MANAGE_CLASS)
    finally:
        session.close()

@router.message(TeacherStates.MANAGE_CLASS, lambda message: message.text.strip() == "Добавить оценку")
async def teacher_add_grade(message: types.Message, state: FSMContext):
    telegram_id = message.from_user.id
    data = await state.get_data()
    class_id = data.get("class_id")
    logging.debug(f"Teacher add grade requested by telegram_id={telegram_id}, class_id={class_id}")

    session = create_session()
    try:
        students = session.query(Student).filter(Student.class_id == class_id).all()
        if not students:
            logging.debug(f"No students found for class_id={class_id}")
            await message.answer("Ученики не найдены.", reply_markup=get_manage_class_keyboard())
            await state.set_state(TeacherStates.MANAGE_CLASS)
            try:
                await message.delete()
            except Exception as e:
                logging.warning(f"Failed to delete message for telegram_id={telegram_id}: {e}")
            return

        keyboard = InlineKeyboardMarkup(inline_keyboard=[], row_width=1)
        for student in students:
            user = session.query(User).filter(User.user_id == student.user_id).first()
            keyboard.inline_keyboard.append(
                [InlineKeyboardButton(text=f"{user.first_name} {user.last_name}", callback_data=f"grade_student_{student.user_id}")]
            )

        await state.set_state(TeacherStates.ADD_GRADE_SELECT_STUDENT)
        try:
            await message.delete()
        except Exception as e:
            logging.warning(f"Failed to delete message for telegram_id={telegram_id}: {e}")
        await message.answer("Выберите ученика:", reply_markup=keyboard)
    except Exception as e:
        logging.error(f"Error in teacher_add_grade for telegram_id={telegram_id}: {e}")
        await message.answer("Произошла ошибка. Попробуйте снова.", reply_markup=get_manage_class_keyboard())
        await state.set_state(TeacherStates.MANAGE_CLASS)
    finally:
        session.close()

@router.callback_query(TeacherStates.ADD_GRADE_SELECT_STUDENT, lambda c: c.data.startswith("grade_student_"))
async def process_grade_student_selection(callback_query: types.CallbackQuery, state: FSMContext):
    try:
        student_id = int(callback_query.data.split("_")[2])
        telegram_id = callback_query.from_user.id
        logging.debug(f"Student selected for grade: student_id={student_id} by telegram_id={telegram_id}")

        await state.update_data(student_id=student_id)
        await state.set_state(TeacherStates.ADD_GRADE_ENTER_GRADE)
        try:
            await callback_query.message.delete()
        except Exception as e:
            logging.warning(f"Failed to delete message for telegram_id={telegram_id}: {e}")
        await callback_query.message.answer("Введите оценку (2–5):", reply_markup=types.ReplyKeyboardRemove())
        await callback_query.answer()
    except Exception as e:
        logging.error(f"Error in process_grade_student_selection for telegram_id={telegram_id}: {e}")
        await callback_query.message.answer("Ошибка обработки. Попробуйте снова.", reply_markup=get_manage_class_keyboard())
        await state.set_state(TeacherStates.MANAGE_CLASS)
        await callback_query.answer()

@router.message(TeacherStates.ADD_GRADE_ENTER_GRADE)
async def process_grade_input(message: types.Message, state: FSMContext):
    telegram_id = message.from_user.id
    grade_text = message.text.strip()
    logging.debug(f"Grade input received: {grade_text} by telegram_id={telegram_id}")

    try:
        grade = int(grade_text)
        if grade < 2 or grade > 5:
            await message.answer("Пожалуйста, введите оценку от 2 до 5.", reply_markup=types.ReplyKeyboardRemove())
            return
        await state.update_data(grade=grade)
        await state.set_state(TeacherStates.ADD_GRADE_ENTER_DATE)
        try:
            await message.delete()
        except Exception as e:
            logging.warning(f"Failed to delete message for telegram_id={telegram_id}: {e}")
        await message.answer("Введите дату оценки (ГГГГ-ММ-ДД):", reply_markup=types.ReplyKeyboardRemove())
    except ValueError:
        logging.debug(f"Invalid grade input: {grade_text} by telegram_id={telegram_id}")
        await message.answer("Пожалуйста, введите числовую оценку (2–5).", reply_markup=types.ReplyKeyboardRemove())
    except Exception as e:
        logging.error(f"Error in process_grade_input for telegram_id={telegram_id}: {e}")
        await message.answer("Произошла ошибка. Попробуйте снова.", reply_markup=get_manage_class_keyboard())
        await state.set_state(TeacherStates.MANAGE_CLASS)

@router.message(TeacherStates.ADD_GRADE_ENTER_DATE)
async def process_grade_date(message: types.Message, state: FSMContext):
    telegram_id = message.from_user.id
    date_text = message.text.strip()
    data = await state.get_data()
    student_id = data.get("student_id")
    grade = data.get("grade")
    subject_id = data.get("subject_id")
    class_id = data.get("class_id")
    logging.debug(f"Date input received: {date_text} for student_id={student_id}, grade={grade}, subject_id={subject_id} by telegram_id={telegram_id}")

    session = create_session()
    try:
        grade_date = datetime.strptime(date_text, "%Y-%m-%d").date()
        new_grade = Grade(
            student_id=student_id,
            subject_id=subject_id,
            grade=grade,
            date=grade_date
        )
        session.add(new_grade)
        session.commit()
        logging.debug(f"Grade added: student_id={student_id}, subject_id={subject_id}, grade={grade}, date={date_text}")

        try:
            await message.delete()
        except Exception as e:
            logging.warning(f"Failed to delete message for telegram_id={telegram_id}: {e}")
        await message.answer("Оценка успешно добавлена.", reply_markup=get_manage_class_keyboard())
        await state.set_state(TeacherStates.MANAGE_CLASS)
        await state.update_data(subject_id=subject_id, class_id=class_id)
    except ValueError:
        logging.debug(f"Invalid date format: {date_text} by telegram_id={telegram_id}")
        await message.answer("Пожалуйста, введите дату в формате ГГГГ-ММ-ДД (например, 2025-05-18).", reply_markup=types.ReplyKeyboardRemove())
    except Exception as e:
        logging.error(f"Error in process_grade_date for telegram_id={telegram_id}: {e}")
        await message.answer("Произошла ошибка при добавлении оценки. Попробуйте снова.", reply_markup=get_manage_class_keyboard())
        await state.set_state(TeacherStates.MANAGE_CLASS)
        await state.update_data(subject_id=subject_id, class_id=class_id)
    finally:
        session.close()

@router.message(TeacherStates.MANAGE_CLASS, lambda message: message.text.strip() == "Просмотреть посещаемость")
async def teacher_view_attendance(message: types.Message, state: FSMContext):
    data = await state.get_data()
    class_id = data.get("class_id")
    telegram_id = message.from_user.id
    logging.debug(f"Teacher attendance requested: class_id={class_id} by telegram_id={telegram_id}")

    session = create_session()
    try:
        attendance = session.query(Attendance).join(Student).filter(Student.class_id == class_id).all()
        if not attendance:
            logging.debug(f"No attendance records found for class_id={class_id}")
            await message.answer("Записи о посещаемости не найдены.", reply_markup=get_manage_class_keyboard())
            return

        response = "Посещаемость:\n"
        for att in attendance:
            student = session.query(Student).filter(Student.user_id == att.student_id).first()
            user = session.query(User).filter(User.user_id == student.user_id).first()
            response += f"{user.first_name} {user.last_name} - {att.date}: {att.status}\n"

        try:
            await message.delete()
        except Exception as e:
            logging.warning(f"Failed to delete message for telegram_id={telegram_id}: {e}")
        await message.answer(response, reply_markup=get_manage_class_keyboard())
        await state.set_state(TeacherStates.MANAGE_CLASS)
    except Exception as e:
        logging.error(f"Error in teacher_view_attendance for telegram_id={telegram_id}: {e}")
        await message.answer("Произошла ошибка. Попробуйте снова.", reply_markup=get_manage_class_keyboard())
        await state.set_state(TeacherStates.MANAGE_CLASS)
    finally:
        session.close()

@router.message(TeacherStates.MANAGE_CLASS, lambda message: message.text.strip() == "Добавить посещаемость")
async def teacher_add_attendance(message: types.Message, state: FSMContext):
    telegram_id = message.from_user.id
    data = await state.get_data()
    class_id = data.get("class_id")
    logging.debug(f"Teacher add attendance requested by telegram_id={telegram_id}, class_id={class_id}")

    session = create_session()
    try:
        students = session.query(Student).filter(Student.class_id == class_id).all()
        if not students:
            logging.debug(f"No students found for class_id={class_id}")
            await message.answer("Ученики не найдены.", reply_markup=get_manage_class_keyboard())
            await state.set_state(TeacherStates.MANAGE_CLASS)
            try:
                await message.delete()
            except Exception as e:
                logging.warning(f"Failed to delete message for telegram_id={telegram_id}: {e}")
            return

        keyboard = InlineKeyboardMarkup(inline_keyboard=[], row_width=1)
        for student in students:
            user = session.query(User).filter(User.user_id == student.user_id).first()
            keyboard.inline_keyboard.append(
                [InlineKeyboardButton(text=f"{user.first_name} {user.last_name}", callback_data=f"att_student_{student.user_id}")]
            )

        await state.set_state(TeacherStates.ADD_ATTENDANCE_SELECT_STUDENT)
        try:
            await message.delete()
        except Exception as e:
            logging.warning(f"Failed to delete message for telegram_id={telegram_id}: {e}")
        await message.answer("Выберите ученика:", reply_markup=keyboard)
    except Exception as e:
        logging.error(f"Error in teacher_add_attendance for telegram_id={telegram_id}: {e}")
        await message.answer("Произошла ошибка. Попробуйте снова.", reply_markup=get_manage_class_keyboard())
        await state.set_state(TeacherStates.MANAGE_CLASS)
    finally:
        session.close()

@router.callback_query(TeacherStates.ADD_ATTENDANCE_SELECT_STUDENT, lambda c: c.data.startswith("att_student_"))
async def process_attendance_student_selection(callback_query: types.CallbackQuery, state: FSMContext):
    try:
        student_id = int(callback_query.data.split("_")[2])
        telegram_id = callback_query.from_user.id
        logging.debug(f"Student selected for attendance: student_id={student_id} by telegram_id={telegram_id}")

        keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="Присутствовал"), KeyboardButton(text="Отсутствовал")]
            ],
            resize_keyboard=True,
            row_width=2
        )

        await state.update_data(student_id=student_id)
        await state.set_state(TeacherStates.ADD_ATTENDANCE_ENTER_STATUS)
        try:
            await callback_query.message.delete()
        except Exception as e:
            logging.warning(f"Failed to delete message for telegram_id={telegram_id}: {e}")
        await callback_query.message.answer("Выберите статус посещаемости:", reply_markup=keyboard)
        await callback_query.answer()
    except Exception as e:
        logging.error(f"Error in process_attendance_student_selection for telegram_id={telegram_id}: {e}")
        await callback_query.message.answer("Ошибка обработки. Попробуйте снова.", reply_markup=get_manage_class_keyboard())
        await state.set_state(TeacherStates.MANAGE_CLASS)
        await callback_query.answer()

@router.message(TeacherStates.ADD_ATTENDANCE_ENTER_STATUS, lambda message: message.text.strip() in ["Присутствовал", "Отсутствовал"])
async def process_attendance_status(message: types.Message, state: FSMContext):
    telegram_id = message.from_user.id
    status = message.text.strip()
    logging.debug(f"Attendance status received: {status} by telegram_id={telegram_id}")

    await state.update_data(status=status)
    await state.set_state(TeacherStates.ADD_ATTENDANCE_ENTER_DATE)
    try:
        await message.delete()
    except Exception as e:
        logging.warning(f"Failed to delete message for telegram_id={telegram_id}: {e}")
    await message.answer("Введите дату посещаемости (ГГГГ-ММ-ДД):", reply_markup=types.ReplyKeyboardRemove())

@router.message(TeacherStates.ADD_ATTENDANCE_ENTER_STATUS)
async def process_invalid_attendance_status(message: types.Message, state: FSMContext):
    telegram_id = message.from_user.id
    logging.debug(f"Invalid attendance status received: {message.text} by telegram_id={telegram_id}")
    await message.answer("Пожалуйста, выберите 'Присутствовал' или 'Отсутствовал'.")

@router.message(TeacherStates.ADD_ATTENDANCE_ENTER_DATE)
async def process_attendance_date(message: types.Message, state: FSMContext):
    telegram_id = message.from_user.id
    date_text = message.text.strip()
    data = await state.get_data()
    student_id = data.get("student_id")
    status = data.get("status")
    subject_id = data.get("subject_id")
    class_id = data.get("class_id")
    logging.debug(f"Date input received: {date_text} for student_id={student_id}, status={status} by telegram_id={telegram_id}")

    session = create_session()
    try:
        att_date = datetime.strptime(date_text, "%Y-%m-%d").date()
        new_attendance = Attendance(
            student_id=student_id,
            date=att_date,
            status=status
        )
        session.add(new_attendance)
        session.commit()
        logging.debug(f"Attendance added: student_id={student_id}, status={status}, date={date_text}")

        try:
            await message.delete()
        except Exception as e:
            logging.warning(f"Failed to delete message for telegram_id={telegram_id}: {e}")
        await message.answer("Посещаемость успешно добавлена.", reply_markup=get_manage_class_keyboard())
        await state.set_state(TeacherStates.MANAGE_CLASS)
        await state.update_data(subject_id=subject_id, class_id=class_id)
    except ValueError:
        logging.debug(f"Invalid date format: {date_text} by telegram_id={telegram_id}")
        await message.answer("Пожалуйста, введите дату в формате ГГГГ-ММ-ДД (например, 2025-05-18).", reply_markup=types.ReplyKeyboardRemove())
    except Exception as e:
        logging.error(f"Error in process_attendance_date for telegram_id={telegram_id}: {e}")
        await message.answer("Произошла ошибка при добавлении посещаемости. Попробуйте снова.", reply_markup=get_manage_class_keyboard())
        await state.set_state(TeacherStates.MANAGE_CLASS)
        await state.update_data(subject_id=subject_id, class_id=class_id)
    finally:
        session.close()

@router.message(TeacherStates.MANAGE_CLASS, lambda message: message.text.strip() == "Добавить ДЗ")
async def teacher_add_homework(message: types.Message, state: FSMContext):
    telegram_id = message.from_user.id
    logging.debug(f"Teacher add homework requested by telegram_id={telegram_id}")

    await state.set_state(TeacherStates.ADD_HOMEWORK_ENTER_TASK)
    try:
        await message.delete()
    except Exception as e:
        logging.warning(f"Failed to delete message for telegram_id={telegram_id}: {e}")
    await message.answer("Введите текст домашнего задания:", reply_markup=types.ReplyKeyboardRemove())

@router.message(TeacherStates.ADD_HOMEWORK_ENTER_TASK)
async def process_homework_task(message: types.Message, state: FSMContext):
    telegram_id = message.from_user.id
    task = message.text.strip()
    logging.debug(f"Homework task received: {task} by telegram_id={telegram_id}")

    if not task:
        await message.answer("Пожалуйста, введите непустой текст задания.", reply_markup=types.ReplyKeyboardRemove())
        return

    await state.update_data(task=task)
    await state.set_state(TeacherStates.ADD_HOMEWORK_ENTER_DUE_DATE)
    try:
        await message.delete()
    except Exception as e:
        logging.warning(f"Failed to delete message for telegram_id={telegram_id}: {e}")
    await message.answer("Введите дату сдачи ДЗ (ГГГГ-ММ-ДД):", reply_markup=types.ReplyKeyboardRemove())

@router.message(TeacherStates.ADD_HOMEWORK_ENTER_DUE_DATE)
async def process_homework_due_date(message: types.Message, state: FSMContext):
    telegram_id = message.from_user.id
    date_text = message.text.strip()
    data = await state.get_data()
    task = data.get("task")
    class_id = data.get("class_id")
    subject_id = data.get("subject_id")
    logging.debug(f"Due date input received: {date_text} for class_id={class_id}, subject_id={subject_id}, task={task} by telegram_id={telegram_id}")

    session = create_session()
    try:
        due_date = datetime.strptime(date_text, "%Y-%m-%d").date()
        new_homework = Homework(
            class_id=class_id,
            subject_id=subject_id,
            task=task,
            due_date=due_date
        )
        session.add(new_homework)
        session.commit()
        logging.debug(f"Homework added: class_id={class_id}, subject_id={subject_id}, task={task}, due_date={date_text}")

        try:
            await message.delete()
        except Exception as e:
            logging.warning(f"Failed to delete message for telegram_id={telegram_id}: {e}")
        await message.answer("Домашнее задание успешно добавлено.", reply_markup=get_manage_class_keyboard())
        await state.set_state(TeacherStates.MANAGE_CLASS)
        await state.update_data(subject_id=subject_id, class_id=class_id)
    except ValueError:
        logging.debug(f"Invalid date format: {date_text} by telegram_id={telegram_id}")
        await message.answer("Пожалуйста, введите дату в формате ГГГГ-ММ-ДД (например, 2025-05-18).", reply_markup=types.ReplyKeyboardRemove())
    except Exception as e:
        logging.error(f"Error in process_homework_due_date for telegram_id={telegram_id}: {e}")
        await message.answer("Произошла ошибка при добавлении ДЗ. Попробуйте снова.", reply_markup=get_manage_class_keyboard())
        await state.set_state(TeacherStates.MANAGE_CLASS)
        await state.update_data(subject_id=subject_id, class_id=class_id)
    finally:
        session.close()

@router.message(TeacherStates.MANAGE_CLASS, lambda message: message.text.strip() == "Назад")
async def teacher_back_to_main(message: types.Message, state: FSMContext):
    telegram_id = message.from_user.id
    logging.debug(f"Teacher back to main requested by telegram_id={telegram_id}")
    await state.set_state(TeacherStates.MAIN_MENU)
    await state.set_data({})
    try:
        await message.delete()
    except Exception as e:
        logging.warning(f"Failed to delete message for telegram_id={telegram_id}: {e}")
    await message.answer("Вернуться в меню:", reply_markup=get_main_menu("teacher"))

@router.message(TeacherStates.MAIN_MENU, lambda message: message.text.strip() == "Информация о классе")
async def teacher_class_info(message: types.Message, state: FSMContext):
    telegram_id = message.from_user.id
    current_state = await state.get_state()
    logging.debug(f"Teacher class info requested by telegram_id={telegram_id}, state={current_state}")
    user_id, role = is_authorized(telegram_id)
    if not user_id or role != "teacher":
        logging.warning(f"Unauthorized access attempt by telegram_id={telegram_id}")
        await message.answer("Пожалуйста, войдите в аккаунт.")
        await state.set_data({})
        await start_command(message, state)
        return

    session = create_session()
    try:
        teacher = session.query(Teacher).filter(Teacher.user_id == user_id).first()
        if not teacher:
            logging.warning(f"No teacher found for user_id={user_id}")
            await message.answer("Данные учителя не найдены.")
            await state.set_data({})
            await start_command(message, state)
            return

        cls = session.query(Class).filter(Class.teacher_id == teacher.teacher_id).first()
        if not cls:
            logging.debug(f"No class found for teacher_id={teacher.teacher_id}")
            await message.answer("Класс не найден.")
            return

        response = f"Класс: {cls.class_name}\n"
        students = session.query(Student).filter(Student.class_id == cls.class_id).all()
        if not students:
            response += "Ученики не найдены.\n"
        else:
            response += "Оценки и посещаемость:\n"
            for student in students:
                user = session.query(User).filter(User.user_id == student.user_id).first()
                response += f"\n{user.first_name} {user.last_name}:\n"
                grades = session.query(Grade).filter(Grade.student_id == student.user_id).all()
                for grade in grades:
                    subject = session.query(Subject).filter(Subject.subject_id == grade.subject_id).first()
                    response += f"  {subject.subject_name if subject else 'Неизвестный предмет'} ({grade.date}): {grade.grade}\n"
                attendance = session.query(Attendance).filter(Attendance.student_id == student.user_id).all()
                for att in attendance:
                    response += f"  Посещаемость ({att.date}): {att.status}\n"

        schedules = session.query(Schedule).filter(Schedule.class_id == cls.class_id).all()
        if schedules:
            schedules = sorted(
                schedules,
                key=lambda sch: (DAY_ORDER.get(sch.day_of_week, 8), sch.start_time)
            )
            response += "\nРасписание:\n"
            for sch in schedules:
                subject = session.query(Subject).filter(Subject.subject_id == sch.subject_id).first()
                response += f"{sch.day_of_week} {sch.start_time}-{sch.end_time}: {subject.subject_name if subject else 'Неизвестный предмет'}\n"
        else:
            response += "\nРасписание не найдено.\n"

        try:
            await message.delete()
        except Exception as e:
            logging.warning(f"Failed to delete message for telegram_id={telegram_id}: {e}")
        await message.answer(response, reply_markup=get_main_menu("teacher"))
        await state.set_state(TeacherStates.MAIN_MENU)
        await state.set_data({})
    except Exception as e:
        logging.error(f"Error in teacher_class_info for telegram_id={telegram_id}: {e}")
        await message.answer("Произошла ошибка. Попробуйте снова.")
        await state.set_state(TeacherStates.MAIN_MENU)
        await state.set_data({})
    finally:
        session.close()

@router.message(TeacherStates.MAIN_MENU, lambda message: message.text.strip() == "Расписание")
async def teacher_schedule(message: types.Message, state: FSMContext):
    telegram_id = message.from_user.id
    current_state = await state.get_state()
    logging.debug(f"Teacher schedule requested by telegram_id={telegram_id}, state={current_state}")
    user_id, role = is_authorized(telegram_id)
    if not user_id or role != "teacher":
        logging.warning(f"Unauthorized access attempt by telegram_id={telegram_id}")
        await message.answer("Пожалуйста, войдите в аккаунт.")
        await state.set_data({})
        await start_command(message, state)
        return

    session = create_session()
    try:
        teacher = session.query(Teacher).filter(Teacher.user_id == user_id).first()
        if not teacher:
            logging.warning(f"No teacher found for user_id={user_id}")
            await message.answer("Данные учителя не найдены.")
            await state.set_data({})
            await start_command(message, state)
            return

        schedules = session.query(Schedule).filter(Schedule.teacher_id == teacher.teacher_id).all()
        if not schedules:
            logging.debug(f"No schedules found for teacher_id={teacher.teacher_id}")
            await message.answer("Расписание не найдено.")
            return

        schedules = sorted(
            schedules,
            key=lambda sch: (DAY_ORDER.get(sch.day_of_week, 8), sch.start_time)
        )

        response = "Расписание:\n"
        for sch in schedules:
            subject = session.query(Subject).filter(Subject.subject_id == sch.subject_id).first()
            cls = session.query(Class).filter(Class.class_id == sch.class_id).first()
            response += f"{sch.day_of_week} {sch.start_time}-{sch.end_time}: {subject.subject_name if subject else 'Неизвестный предмет'} ({cls.class_name if cls else 'Неизвестный класс'})\n"

        try:
            await message.delete()
        except Exception as e:
            logging.warning(f"Failed to delete message for telegram_id={telegram_id}: {e}")
        await message.answer(response, reply_markup=get_main_menu("teacher"))
        await state.set_state(TeacherStates.MAIN_MENU)
        await state.set_data({})
    except Exception as e:
        logging.error(f"Error in teacher_schedule for telegram_id={telegram_id}: {e}")
        await message.answer("Произошла ошибка. Попробуйте снова.")
        await state.set_state(TeacherStates.MAIN_MENU)
        await state.set_data({})
    finally:
        session.close()

# Обработчик неизвестных сообщений
@router.message()
async def handle_unknown_message(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    telegram_id = message.from_user.id
    logging.debug(f"Unknown message received: '{message.text}', current_state={current_state}, telegram_id={telegram_id}")
    user_id, role = is_authorized(telegram_id)
    if role == "teacher" and current_state == TeacherStates.MAIN_MENU.state:
        await message.answer("Пожалуйста, выберите действие из меню:", reply_markup=get_main_menu("teacher"))
    elif role == "teacher" and current_state == TeacherStates.MANAGE_CLASS.state:
        await message.answer("Пожалуйста, выберите действие из меню:", reply_markup=get_manage_class_keyboard())
    elif role == "student" and current_state == StudentStates.MAIN_MENU.state:
        await message.answer("Пожалуйста, выберите действие из меню:", reply_markup=get_main_menu("student"))
    else:
        await message.answer("Пожалуйста, используйте кнопки меню.")

# Запуск бота
async def main():
    await dp.start_polling(bot)

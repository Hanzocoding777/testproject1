import logging
import os
import re
import asyncio
import sqlite3

from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler, filters, ContextTypes
from pyrogram import Client
from pyrogram.enums import ParseMode

# Добавьте в начало файла импорты:
from database import Database
#from admin_handlers import admin_command, admin_teams_list, handle_team_action #Удалено

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")

# Define states
(
    CHECKING_SUBSCRIPTION,
    TEAM_NAME,
    PLAYERS_LIST,
    CONFIRMATION,
    CAPTAIN_CONTACTS,
    TOURNAMENT_INFO,
    FAQ,
    REGISTRATION_STATUS,
    WAITING_TEAM_NAME # Add the WAITING_TEAM_NAME state
) = range(9) # Update the range to 9

# Channel ID for subscription check
CHANNEL_ID = "@m5cup"

# Pyrogram Client (UserBot)
userbot = Client(
    name="my_userbot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    parse_mode=ParseMode.HTML
)

# Инициализация базы данных
db = Database()

# Клавиатуры
def get_main_keyboard():
    """Главная клавиатура с основными функциями."""
    keyboard = [
        [KeyboardButton("Регистрация")],
        [KeyboardButton("Информация о турнире")],
        [KeyboardButton("Проверить статус регистрации")],
        [KeyboardButton("FAQ")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_registration_keyboard():
    """Клавиатура для этапа регистрации."""
    keyboard = [
        [KeyboardButton("Проверить подписку")],
        [KeyboardButton("Назад")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_back_keyboard():
    """Простая клавиатура только с кнопкой Назад."""
    keyboard = [
        [KeyboardButton("Назад")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_confirmation_keyboard():
    """Клавиатура для подтверждения списка игроков."""
    keyboard = [
        [KeyboardButton("✅ Продолжить")],
        [KeyboardButton("🔄 Отправить список заново")],
        [KeyboardButton("Назад")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_admin_keyboard():
    """Клавиатура админ-панели."""
    keyboard = [
        [InlineKeyboardButton("📋 Список команд", callback_data="admin_teams_list")],
        [InlineKeyboardButton("➕ Добавить админа", callback_data="admin_add_admin")],
        [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")]
    ]
    return InlineKeyboardMarkup(keyboard)

# Добавьте эти функции в main.py перед функцией main()
async def check_registration_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Проверка статуса регистрации команды."""
    await update.message.reply_text(
        "Для проверки статуса регистрации, пожалуйста, введите название вашей команды:",
        reply_markup=get_back_keyboard()
    )
    return WAITING_TEAM_NAME

async def handle_team_name_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка введенного названия команды для проверки статуса."""
    team_name = update.message.text
    
    if team_name.lower() == "назад":
        await update.message.reply_text(
            "Вы вернулись в главное меню.",
            reply_markup=get_main_keyboard()
        )
        return ConversationHandler.END
        
    team_info = db.get_team_status(team_name)
    
    if not team_info:
        await update.message.reply_text(
            "❌ Команда с таким названием не найдена.\n"
            "Проверьте правильность написания названия или зарегистрируйте команду.",
            reply_markup=get_main_keyboard()
        )
        return ConversationHandler.END

    status_emoji = {
        'pending': '⏳',
        'approved': '✅',
        'rejected': '❌'
    }

    players_list = "\n".join([f"• {p[0]} – {p[1]}" for p in team_info['players']])
    
    message = (
        f"📋 Статус регистрации команды {team_info['team_name']}:\n\n"
        f"Статус: {status_emoji.get(team_info['status'], '❓')} {team_info['status'].title()}\n"
        f"Дата регистрации: {team_info['registration_date']}\n"
        f"\n👥 Состав команды:\n{players_list}\n"
    )

    if team_info['admin_comment']:
        message += f"\n💬 Комментарий администратора:\n{team_info['admin_comment']}"

    await update.message.reply_text(
        message,
        reply_markup=get_main_keyboard()
    )
    return ConversationHandler.END


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Send welcome message and show main menu."""
    welcome_message = """🏆 Добро пожаловать в бота регистрации на турнир

"M5 Domination Cup"


Я помогу вам зарегистрироваться на турнир и предоставлю всю необходимую информацию.


📝 Что я умею:
• Регистрация команды на турнир
• Просмотр информации о турнире
• Проверка статуса регистрации
• Ответы на часто задаваемые вопросы


🎮 Для начала регистрации нажмите кнопку "Регистрация" ниже.
ℹ️ Для получения дополнительной информации выберите "Информация о турнире".


Важно: Убедитесь, что у вас готова следующая информация:
• Название команды
• Список игроков (никнеймы)
• Контактные данные капитана (Дискорд или телеграм)


Удачи в турнире! 🎯"""

    await update.message.reply_text(welcome_message, reply_markup=get_main_keyboard())
    return ConversationHandler.END

async def start_registration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the registration process."""
    await update.message.reply_text(
        "📢 Для участия в M5 Domination Cup необходимо быть подписанным на наш канал!\n\n"
        "🔗 Подпишись на [M5 Cup](https://t.me/m5cup), затем нажми \"Проверить подписку\".\n\n"
        "🛑 Если ты уже подписан, просто нажми \"Проверить подписку\".",
        reply_markup=get_registration_keyboard(),
        parse_mode='Markdown'
    )
    return CHECKING_SUBSCRIPTION

async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Return to main menu."""
    await update.message.reply_text(
        "Вы вернулись в главное меню. Выберите нужное действие:",
        reply_markup=get_main_keyboard()
    )
    return ConversationHandler.END

async def back_to_checking_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Return to subscription checking step."""
    await update.message.reply_text(
        "📢 Для участия в M5 Domination Cup необходимо быть подписанным на наш канал!\n\n"
        "🔗 Подпишись на [M5 Cup](https://t.me/m5cup), затем нажми \"Проверить подписку\".\n\n"
        "🛑 Если ты уже подписан, просто нажми \"Проверить подписку\".",
        reply_markup=get_registration_keyboard(),
        parse_mode='Markdown'
    )
    return CHECKING_SUBSCRIPTION

async def back_to_team_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Return to team name input step."""
    await update.message.reply_text(
        "🎮 Введи название твоей команды.\n\n"
        "✍🏼 Напиши название в ответном сообщении.",
        reply_markup=get_back_keyboard()
    )
    return TEAM_NAME

async def back_to_players_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Return to players list input step."""
    await update.message.reply_text(
        "Укажи состав команды. Тебе нужно указать:\n"
        "1️⃣ 4 основных игрока\n"
        "2️⃣ Запасных игроков (если есть)\n\n"
        "⚠️ Формат:\n"
        "📌 Игровой никнейм – @TelegramUsername\n\n"
        "👀 Пример:\n\n"
        "PlayerOne – @playerone\n"
        "PlayerTwo – @playertwo\n"
        "PlayerThree – @playerthree\n"
        "PlayerFour – @playerfour\n"
        "(5. Запасной – @reserveplayer)\n\n"
        "📩 Отправь список в ответном сообщении.",
        reply_markup=get_back_keyboard()
    )
    return PLAYERS_LIST

async def check_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Check if user is subscribed to the channel."""
    try:
        user_id = update.message.from_user.id
        chat_member = await context.bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)

        if chat_member.status in ['member', 'administrator', 'creator']:
            await update.message.reply_text(
                "🎮 Отлично! Теперь введи название твоей команды.\n\n"
                "✍🏼 Напиши название в ответном сообщении.",
                reply_markup=get_back_keyboard()
            )
            return TEAM_NAME
        else:
            await update.message.reply_text(
                "❌ Вы не подписаны на канал. Пожалуйста, подпишитесь на @m5cup и попробуйте снова.",
                reply_markup=get_registration_keyboard()
            )
            return CHECKING_SUBSCRIPTION

    except Exception as e:
        logger.error(f"Error checking subscription: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при проверке подписки. Пожалуйста, убедитесь, что вы:\n\n"
            "1. Перешли по ссылке в канал\n"
            "2. Подписались на канал\n"
            "3. Нажали кнопку \"Проверить подписку\"\n\n"
            "Если проблема сохраняется, попробуйте позже.",
            reply_markup=get_registration_keyboard()
        )
        return CHECKING_SUBSCRIPTION

async def receive_team_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive and store team name."""
    team_name = update.message.text
    context.user_data['team_name'] = team_name

    await update.message.reply_text(
        "Теперь укажи состав команды. Тебе нужно указать:\n"
        "1️⃣ 4 основных игрока\n"
        "2️⃣ Запасных игроков (если есть)\n\n"
        "⚠️ Формат:\n"
        "📌 Игровой никнейм – @TelegramUsername\n\n"
        "👀 Пример:\n\n"
        "PlayerOne – @playerone\n"
        "PlayerTwo – @playertwo\n"
        "PlayerThree – @playerthree\n"
        "PlayerFour – @playerfour\n"
        "(5. Запасной – @reserveplayer)\n\n"
        "📩 Отправь список в ответном сообщении.",
        reply_markup=get_back_keyboard()
    )
    return PLAYERS_LIST

async def get_tg_id_by_username(username: str):
    """Gets Telegram ID by username using Pyrogram."""
    try:
        users = await userbot.get_users(username)
        if users:
            if isinstance(users, list):
                if users:
                    return users[0].id
                else:
                    return None
            else:
                return users.id
        else:
            return None
    except Exception as e:
        logger.error(f"Error getting Telegram ID for {username}: {e}")
        return None

async def check_players_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Check and validate players list and check subscription status."""
    players_text = update.message.text
    players = []
    player_pattern = re.compile(r"(.+?)\s*[-–]\s*@([a-zA-Z0-9_]+)")

    for line in players_text.split('\n'):
        match = player_pattern.match(line)
        if match:
            nickname = match.group(1).strip()
            username = match.group(2).strip()
            players.append((nickname, username))

    if len(players) < 4:
        await update.message.reply_text(
            "⚠️ Необходимо указать минимум 4 игрока. Пожалуйста, проверьте формат и количество игроков и отправьте список снова.",
            reply_markup=get_back_keyboard()
        )
        return PLAYERS_LIST

    context.user_data['players'] = players

    await update.message.reply_text(
        "⏳ Проверяем подписку игроков на канал. Это может занять некоторое время...",
        reply_markup=ReplyKeyboardRemove()
    )

    unsubscribed_players = []
    subscribed_players = []

    for nickname, username in players:
        telegram_id = await get_tg_id_by_username(username)

        if telegram_id:
            try:
                chat_member = await context.bot.get_chat_member(chat_id=CHANNEL_ID, user_id=telegram_id)
                if chat_member.status in ['member', 'administrator', 'creator']:
                    subscribed_players.append(f"{nickname} – @{username}")
                else:
                    unsubscribed_players.append(f"{nickname} – @{username}")
            except Exception as e:
                logger.error(f"Error checking subscription for user {telegram_id} (Bot API): {e}")
                if "Participant_id_invalid" in str(e):
                    unsubscribed_players.append(f"{nickname} – @{username} (Ошибка проверки)")
                else:
                    unsubscribed_players.append(f"{nickname} – @{username} (Ошибка проверки)")
        else:
            unsubscribed_players.append(f"{nickname} – @{username} (Проверьте правильность юзернейма)")

    if unsubscribed_players:
        message = "⚠️ Следующие игроки не подписаны на канал @m5cup или не удалось проверить их подписку:\n"
        for player in unsubscribed_players:
            message += f"• {player}\n"
        message += "\nПожалуйста, убедитесь, что все игроки подписаны на канал. Некоторые проверки могли не пройти из-за настроек приватности пользователя"
    else:
        message = "✅ Все игроки из списка подписаны на канал @m5cup!"

    # Сохраняем сообщение для повторного использования
    context.user_data['subscription_message'] = message
    
    await update.message.reply_text(message, reply_markup=get_confirmation_keyboard())
    return CONFIRMATION

async def handle_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle player list confirmation."""
    user_choice = update.message.text
    
    if user_choice == "✅ Продолжить":
        await update.message.reply_text(
            "📞 Теперь укажи контакты капитана команды.\n\n"
            "💬 Напиши в ответном сообщении Telegram или Discord капитана.\n\n"
            "👀 Пример:\n"
            "📌 Telegram: @CaptainUsername\n"
            "или\n"
            "📌 Discord: Captain#1234",
            reply_markup=get_back_keyboard()
        )
        return CAPTAIN_CONTACTS
    
    elif user_choice == "🔄 Отправить список заново":
        await update.message.reply_text(
            "🔄 Пожалуйста, отправьте список игроков заново в формате:\n\n"
            "PlayerOne – @playerone\n"
            "PlayerTwo – @playertwo\n"
            "PlayerThree – @playerthree\n"
            "PlayerFour – @playerfour\n"
            "(5. Запасной – @reserveplayer)",
            reply_markup=get_back_keyboard()
        )
        return PLAYERS_LIST
    
    elif user_choice == "Назад":
        return await back_to_players_list(update, context)

async def finish_registration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Complete the registration process."""
    captain_contact = update.message.text
    context.user_data['captain_contact'] = captain_contact

    team_name = context.user_data.get('team_name', 'Не указано')
    players = context.user_data.get('players', [])

    # Save team information to the database
    team_data = {
        'team_name': team_name,
        'players': players,
        'captain_contact': captain_contact,
    }
    db.add_team(team_data)

    registration_info = (
        f"✅ Поздравляем! Ваша команда успешно зарегистрирована на M5 Domination Cup!\n\n"
        f"📋 Информация о регистрации:\n"
        f"🎮 Название команды: {team_name}\n\n"
        f"👥 Состав команды:\n"
    )

    for nickname, username in players:
        registration_info += f"• {nickname} – @{username}\n"

    registration_info += f"\n👨‍✈️ Контакты капитана:\n{captain_contact}\n\n"
    registration_info += "📢 Вскоре мы свяжемся с капитаном для подтверждения участия.\n\n"
    registration_info += "🔥 Удачи в турнире! 🎮🏆"

    await update.message.reply_text(registration_info, reply_markup=get_main_keyboard())
    return ConversationHandler.END

async def tournament_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show tournament information."""
    await update.message.reply_text(
        "🏆 M5 Domination Cup\n\n"
        "📅 Информация о турнире будет добавлена позже.",
        reply_markup=get_back_keyboard()
    )
    return TOURNAMENT_INFO

async def faq(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show FAQ."""
    await update.message.reply_text(
        "❓ Часто задаваемые вопросы:\n\n"
        "Информация будет добавлена позже.",
        reply_markup=get_back_keyboard()
    )
    return FAQ

async def post_init(application: Application):
    """Post initialization hook to start the Pyrogram client."""
    print("Starting Pyrogram client...")
    # Initialize the database connection
    application.bot_data['db'] = db  # Store the db object in bot_data

    await userbot.start()
    print("Pyrogram client started.")

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показать админ-панель."""
    # Временно отключаем проверку админа:
    #if not db.is_admin(update.effective_user.id):
    #    await update.message.reply_text("У вас нет доступа к админ-панели.")
    #    return

    await update.message.reply_text(
        "🔐 Админ-панель\n\nВыберите действие:",
        reply_markup=get_admin_keyboard()
    )

async def handle_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик кнопок админ-панели"""
    query = update.callback_query
    if not db.is_admin(query.from_user.id):
        await query.answer("У вас нет доступа к этой функции.")
        return

    action = query.data

    if action == "back_to_admin":
        await query.edit_message_text(
            "🔐 Админ-панель\n\nВыберите действие:",
            reply_markup=get_admin_keyboard()
        )
    elif action == "cancel_comment":
        await query.edit_message_text(
            "❌ Добавление комментария отменено.",
            reply_markup=get_admin_keyboard()
        )
    elif action.startswith("comment_team_"):
        team_id = int(action.split('_')[2])
        context.user_data['commenting_team_id'] = team_id
        await query.edit_message_text(
            "💬 Введите комментарий для команды:",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("❌ Отмена", callback_data="cancel_comment")
            ]])
        )
    elif action == "admin_teams_list":
        teams = db.get_all_teams()
        if not teams:
            await query.edit_message_text(
                "📋 Зарегистрированных команд пока нет.",
                reply_markup=get_admin_keyboard()
            )
            return

        # Отправляем список команд отдельными сообщениями
        for team in teams:
            keyboard = [
                [
                    InlineKeyboardButton("✅ Одобрить", callback_data=f"approve_team_{team['id']}"),
                    InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_team_{team['id']}")
                ],
                [InlineKeyboardButton("💬 Комментарий", callback_data=f"comment_team_{team['id']}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            players_list = "\n".join([f"• {p[0]} – {p[1]}" for p in team['players']])
            message = (
                f"🎮 Команда: {team['team_name']}\n"
                f"📅 Дата регистрации: {team['registration_date']}\n"
                f"📱 Контакт капитана: {team['captain_contact']}\n"
                f"📊 Статус: {team['status']}\n"
                f"💭 Комментарий: {team['admin_comment'] or 'Нет'}\n\n"
                f"👥 Игроки:\n{players_list}"
            )

            try:
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=message,
                    reply_markup=reply_markup
                )
            except Exception as e:
                logger.error(f"Error sending team info: {e}")

        # Отправляем сообщение о завершении списка
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="✅ Все команды показаны.",
            reply_markup=get_admin_keyboard()
        )
        return

    elif action == "admin_add_admin":
        await query.edit_message_text(
            "👤 Чтобы добавить нового администратора, отправьте его Telegram ID.\n"
            "❓ Как получить Telegram ID:\n"
            "1. Перешлите сообщение пользователя боту @getmyid_bot\n"
            "2. Или попросите пользователя написать /start боту @getmyid_bot",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("« Назад", callback_data="back_to_admin")
            ]])
        )
        context.user_data['awaiting_admin_id'] = True

    elif action == "admin_stats":
        # Получаем статистику из базы данных
        stats = await get_tournament_stats()
        stats_message = (
            "📊 Статистика турнира:\n\n"
            f"Всего команд: {stats['total_teams']}\n"
            f"Одобренных команд: {stats['approved_teams']}\n"
            f"Ожидают проверки: {stats['pending_teams']}\n"
            f"Отклонено: {stats['rejected_teams']}\n"
            f"Всего игроков: {stats['total_players']}\n\n"
            f"Последняя регистрация: {stats['last_registration']}"
        )
        
        await query.edit_message_text(
            stats_message,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("« Назад", callback_data="back_to_admin")
            ]])
        )


    await query.answer()

async def handle_admin_comment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка комментария от администратора"""
    if not db.is_admin(update.effective_user.id):
        await update.message.reply_text("У вас нет доступа к этой функции.")
        return

    team_id = context.user_data.get('commenting_team_id')
    if not team_id:
        await update.message.reply_text(
            "❌ Ошибка: не найдена команда для комментирования.",
            reply_markup=get_admin_keyboard()
        )
        return

    comment = update.message.text
    if db.update_team_status(team_id, status=None, comment=comment):
        await update.message.reply_text(
            "✅ Комментарий успешно добавлен!",
            reply_markup=get_admin_keyboard()
        )
    else:
        await update.message.reply_text(
            "❌ Ошибка при добавлении комментария.",
            reply_markup=get_admin_keyboard()
        )

    # Очищаем данные о комментируемой команде
    if 'commenting_team_id' in context.user_data:
        del context.user_data['commenting_team_id']

async def get_tournament_stats():
    """Получение статистики турнира"""
    stats = {
        'total_teams': 0,
        'approved_teams': 0,
        'pending_teams': 0,
        'rejected_teams': 0,
        'total_players': 0,
        'last_registration': 'Нет регистраций'
    }
    
    try:
        with sqlite3.connect(db.db_file) as conn:
            cursor = conn.cursor()
            
            # Общее количество команд и статусы
            cursor.execute('''
                SELECT status, COUNT(*) 
                FROM teams 
                GROUP BY status
            ''')
            for status, count in cursor.fetchall():
                stats['total_teams'] += count
                if status == 'approved':
                    stats['approved_teams'] = count
                elif status == 'pending':
                    stats['pending_teams'] = count
                elif status == 'rejected':
                    stats['rejected_teams'] = count
            
            # Общее количество игроков
            cursor.execute('SELECT COUNT(*) FROM players')
            stats['total_players'] = cursor.fetchone()[0]
            
            # Последняя регистрация
            cursor.execute('''
                SELECT team_name, registration_date 
                FROM teams 
                ORDER BY registration_date DESC 
                LIMIT 1
            ''')
            last_team = cursor.fetchone()
            if last_team:
                stats['last_registration'] = f"{last_team[0]} ({last_team[1]})"
            
    except Exception as e:
        logger.error(f"Error getting tournament stats: {e}")
    
    return stats

async def admin_add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Добавить админа."""
    # Временно добавляем функциональность для добавления админа:
    user_id_to_add = 123456789  # Замените на ваш Telegram User ID
    username_to_add = "@yourusername" # Замените на ваш username
    if db.add_admin(user_id_to_add, username_to_add):
        await update.callback_query.answer(f"Админ с ID {user_id_to_add} успешно добавлен.")
    else:
        await update.callback_query.answer(f"Пользователь с ID {user_id_to_add} уже является админом.")

# В функции main() обновите обработчики:
def main() -> None:
    application = Application.builder().token(BOT_TOKEN).post_init(post_init).build()

    # Store the database object in bot_data for access in handlers
    application.bot_data['db'] = db

    # Обновляем обработчики для админ-панели
    application.add_handler(CommandHandler("admin", admin_command))
    
    # Обновляем паттерн для callback-обработчика
    application.add_handler(CallbackQueryHandler(
        handle_admin_callback,
        pattern="^(admin_|back_to_admin|cancel_comment|comment_team_)"
    ))
    
    # Добавляем обработчик для действий с командами
    application.add_handler(CallbackQueryHandler(
        handle_team_action,
        pattern="^(approve_team_|reject_team_)"
    ))
    
    # Добавляем обработчик для текстовых сообщений от админов (комментарии)
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE,
        handle_admin_comment
    ))

    # Обновляем ConversationHandler
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('start', start),
            MessageHandler(filters.Regex('^Регистрация$'), start_registration),
            MessageHandler(filters.Regex('^Информация о турнире$'), tournament_info),
            MessageHandler(filters.Regex('^Проверить статус регистрации$'), check_registration_status),
            MessageHandler(filters.Regex('^FAQ$'), faq),
        ],
        states={
            CHECKING_SUBSCRIPTION: [
                MessageHandler(filters.Regex('^Проверить подписку$'), check_subscription),
                MessageHandler(filters.Regex('^Назад$'), back_to_main),
            ],
            TEAM_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex('^Назад$'), receive_team_name),
                MessageHandler(filters.Regex('^Назад$'), back_to_checking_subscription),
            ],
            PLAYERS_LIST: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex('^Назад$'), check_players_subscription),
                MessageHandler(filters.Regex('^Назад$'), back_to_team_name),
            ],
            CONFIRMATION: [
                MessageHandler(filters.Regex('^✅ Продолжить$|^🔄 Отправить список заново$|^Назад$'), handle_confirmation),
            ],
            CAPTAIN_CONTACTS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex('^Назад$'), finish_registration),
                MessageHandler(filters.Regex('^Назад$'), back_to_players_list),
            ],
            TOURNAMENT_INFO: [
                MessageHandler(filters.Regex('^Назад$'), back_to_main),
            ],
            REGISTRATION_STATUS: [
                MessageHandler(filters.Regex('^Назад$'), back_to_main),
            ],
            FAQ: [
                MessageHandler(filters.Regex('^Назад$'), back_to_main),
            ],
            WAITING_TEAM_NAME: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND & ~filters.Regex('^Назад$'),
                    handle_team_name_status
                ),
                 MessageHandler(filters.Regex('^Назад$'), back_to_main),
            ],
        },
        fallbacks=[CommandHandler('start', start)],
    )

    application.add_handler(conv_handler)

    # Start the Bot
    application.run_polling()
    
    # Остановка Pyrogram клиента при выходе
    asyncio.run(userbot.stop())

if __name__ == '__main__':
    main()
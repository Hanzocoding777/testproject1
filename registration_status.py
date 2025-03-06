from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes
from database import Database

db = Database()

async def check_registration_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Проверка статуса регистрации команды."""
    await update.message.reply_text(
        "Для проверки статуса регистрации, пожалуйста, введите название вашей команды:"
    )
    return "WAITING_TEAM_NAME"

async def handle_team_name_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка введенного названия команды для проверки статуса."""
    team_name = update.message.text
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
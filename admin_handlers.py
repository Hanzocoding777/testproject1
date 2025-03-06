from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from database import Database

db = Database()

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показать админ-панель."""
    if not db.is_admin(update.effective_user.id):
        await update.message.reply_text("У вас нет доступа к админ-панели.")
        return

    keyboard = [
        [InlineKeyboardButton("📋 Список команд", callback_data="admin_teams_list")],
        [InlineKeyboardButton("➕ Добавить админа", callback_data="admin_add_admin")],
        [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🔐 Админ-панель\n\nВыберите действие:",
        reply_markup=reply_markup
    )

async def admin_teams_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показать список всех команд."""
    query = update.callback_query
    if not db.is_admin(query.from_user.id):
        await query.answer("У вас нет доступа к этой функции.")
        return

    teams = db.get_all_teams()
    
    if not teams:
        await query.edit_message_text("Зарегистрированных команд пока нет.")
        return

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
        
        await query.message.reply_text(message, reply_markup=reply_markup)

    await query.answer()

async def handle_team_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка действий с командами (одобрение/отклонение)"""
    query = update.callback_query
    
    # Проверка на админа временно отключена для тестирования
    # if not db.is_admin(query.from_user.id):
    #     await query.answer("У вас нет доступа к этой функции.")
    #     return

    action = query.data
    if action.startswith(("approve_team_", "reject_team_")):
        team_id = int(action.split('_')[2])
        status = 'approved' if action.startswith('approve') else 'rejected'
        
        if db.update_team_status(team_id, status=status):
            status_emoji = '✅' if status == 'approved' else '❌'
            await query.answer(f"{status_emoji} Статус команды обновлен!")
            
            # Обновляем сообщение с информацией о команде
            team_info = db.get_team_by_id(team_id)
            if team_info:
                keyboard = [
                    [
                        InlineKeyboardButton("✅ Одобрить", callback_data=f"approve_team_{team_id}"),
                        InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_team_{team_id}")
                    ],
                    [InlineKeyboardButton("💬 Комментарий", callback_data=f"comment_team_{team_id}")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                players_list = "\n".join([f"• {p[0]} – {p[1]}" for p in team_info['players']])
                message = (
                    f"🎮 Команда: {team_info['team_name']}\n"
                    f"📅 Дата регистрации: {team_info['registration_date']}\n"
                    f"📱 Контакт капитана: {team_info['captain_contact']}\n"
                    f"📊 Статус: {status}\n"
                    f"💭 Комментарий: {team_info['admin_comment'] or 'Нет'}\n\n"
                    f"👥 Игроки:\n{players_list}"
                )
                
                await query.edit_message_text(
                    text=message,
                    reply_markup=reply_markup
                )
        else:
            await query.answer("❌ Ошибка при обновлении статуса команды")
    
    await query.answer()
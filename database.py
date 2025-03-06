import sqlite3
from datetime import datetime
from typing import List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)  # Initialize logger

class Database:
    def __init__(self, db_file: str = "tournament.db"):
        self.db_file = db_file
        self.init_db()

    def init_db(self):
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()

            # Таблица команд
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS teams (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    team_name TEXT NOT NULL,
                    captain_contact TEXT NOT NULL,
                    registration_date TIMESTAMP NOT NULL,
                    status TEXT DEFAULT 'pending',
                    admin_comment TEXT
                )
            ''')

            # Таблица игроков
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS players (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    team_id INTEGER,
                    nickname TEXT NOT NULL,
                    telegram_username TEXT NOT NULL,
                    is_captain BOOLEAN DEFAULT 0,
                    FOREIGN KEY (team_id) REFERENCES teams (id)
                )
            ''')

            # Таблица администраторов
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS admins (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER UNIQUE NOT NULL,
                    username TEXT,
                    added_date TIMESTAMP NOT NULL
                )
            ''')

            conn.commit()

    def register_team(self, team_name: str, players: List[Tuple[str, str]], captain_contact: str) -> int:
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()

            # Добавляем команду
            cursor.execute('''
                INSERT INTO teams (team_name, captain_contact, registration_date)
                VALUES (?, ?, ?)
            ''', (team_name, captain_contact, datetime.utcnow()))

            team_id = cursor.lastrowid

            # Добавляем игроков
            for nickname, username in players:
                cursor.execute('''
                    INSERT INTO players (team_id, nickname, telegram_username)
                    VALUES (?, ?, ?)
                ''', (team_id, nickname, username))

            conn.commit()
            return team_id

    def get_team_status(self, team_name: str) -> Optional[dict]:
        with sqlite3.connect(self.db_file) as conn:
            conn.row_factory = sqlite3.Row # allows you to access the database by key names as a dictionary
            cursor = conn.cursor()

            cursor.execute('''
                SELECT t.id, t.team_name, t.status, t.registration_date, t.admin_comment
                FROM teams t
                WHERE t.team_name = ?
            ''', (team_name,))

            team = cursor.fetchone()
            if not team:
                return None

            cursor.execute('''
                SELECT nickname, telegram_username
                FROM players
                WHERE team_id = ?
            ''', (team['id'],)) # use dictionary key name

            players = cursor.fetchall()

            return {
                'team_name': team['team_name'], # use dictionary key name
                'status': team['status'], # use dictionary key name
                'registration_date': team['registration_date'], # use dictionary key name
                'admin_comment': team['admin_comment'], # use dictionary key name
                'players': [(player['nickname'], player['telegram_username']) for player in players] # use dictionary key name
            }

    def add_admin(self, telegram_id: int, username: str = None) -> bool:
        """Добавление нового администратора"""
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO admins (telegram_id, username, added_date)
                    VALUES (?, ?, ?)
                ''', (telegram_id, username, datetime.utcnow()))
                conn.commit()
                return True
        except sqlite3.IntegrityError:
            return False
        except Exception as e:
            logger.error(f"Error adding admin: {e}")
            return False

    def is_admin(self, telegram_id: int) -> bool:
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT 1 FROM admins WHERE telegram_id = ?', (telegram_id,))
            return cursor.fetchone() is not None

    def get_team_by_id(self, team_id: int) -> dict:
        """Получение информации о команде по ID"""
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                
                # Получаем информацию о команде
                cursor.execute('''
                    SELECT id, team_name, captain_contact, registration_date, status, admin_comment
                    FROM teams
                    WHERE id = ?
                ''', (team_id,))
                
                team_row = cursor.fetchone()
                if not team_row:
                    return None
                    
                # Получаем список игроков команды
                cursor.execute('''
                    SELECT nickname, telegram_username
                    FROM players
                    WHERE team_id = ?
                ''', (team_id,))
                
                players = cursor.fetchall()
                
                return {
                    'id': team_row[0],
                    'team_name': team_row[1],
                    'captain_contact': team_row[2],
                    'registration_date': team_row[3],
                    'status': team_row[4],
                    'admin_comment': team_row[5],
                    'players': players
                }
                
        except Exception as e:
            logger.error(f"Error getting team by ID: {e}")
            return None

    def update_team_status(self, team_id: int, status: str = None, comment: str = None) -> bool:
        """Обновляет статус и/или комментарий команды"""
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                
                if status and comment:
                    cursor.execute('''
                        UPDATE teams 
                        SET status = ?, admin_comment = ?
                        WHERE id = ?
                    ''', (status, comment, team_id))
                elif status:
                    cursor.execute('''
                        UPDATE teams 
                        SET status = ?
                        WHERE id = ?
                    ''', (status, team_id))
                elif comment:
                    cursor.execute('''
                        UPDATE teams 
                        SET admin_comment = ?
                        WHERE id = ?
                    ''', (comment, team_id))
                
                conn.commit()
                return cursor.rowcount > 0
                
        except Exception as e:
            logger.error(f"Error updating team status/comment: {e}")
            return False

    def get_all_teams(self) -> list:
        """Получение списка всех команд"""
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT t.id, t.team_name, t.status, t.registration_date, 
                        t.captain_contact, t.admin_comment
                    FROM teams t
                    ORDER BY t.registration_date DESC
                ''')
                
                teams = []
                for team in cursor.fetchall():
                    cursor.execute('''
                        SELECT nickname, telegram_username
                        FROM players
                        WHERE team_id = ?
                    ''', (team[0],))
                    
                    players = cursor.fetchall()
                    teams.append({
                        'id': team[0],
                        'team_name': team[1],
                        'status': team[2],
                        'registration_date': team[3],
                        'captain_contact': team[4],
                        'admin_comment': team[5],
                        'players': players
                    })
                
                return teams
        except Exception as e:
            logger.error(f"Error getting teams: {e}")
            return []
        
    

    def add_team(self, team_data: dict) -> bool:
        """
        Добавляет новую команду в базу данных.

        Args:
            team_data (dict): Словарь с данными команды:
                - team_name (str): Название команды
                - players (list): Список кортежей (nickname, telegram_username)
                - captain_contact (str): Контакты капитана

        Returns:
            bool: True если команда успешно добавлена, False в случае ошибки
        """
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()

                # Добавляем команду
                cursor.execute('''
                    INSERT INTO teams (team_name, captain_contact, registration_date, status)
                    VALUES (?, ?, ?, ?)
                ''', (
                    team_data['team_name'],
                    team_data['captain_contact'],
                    datetime.utcnow(),
                    'pending'
                ))

                team_id = cursor.lastrowid

                # Добавляем игроков
                for nickname, username in team_data['players']:
                    cursor.execute('''
                        INSERT INTO players (team_id, nickname, telegram_username)
                        VALUES (?, ?, ?)
                    ''', (team_id, nickname, username))

                conn.commit()
                return True

        except Exception as e:
            logger.error(f"Error adding team to database: {e}")
            return False
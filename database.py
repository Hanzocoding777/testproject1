import sqlite3
from datetime import datetime
from typing import List, Tuple, Optional

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
            ''', (team[0],))
            
            players = cursor.fetchall()
            
            return {
                'team_name': team[1],
                'status': team[2],
                'registration_date': team[3],
                'admin_comment': team[4],
                'players': players
            }

    def add_admin(self, telegram_id: int, username: str) -> bool:
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

    def is_admin(self, telegram_id: int) -> bool:
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT 1 FROM admins WHERE telegram_id = ?', (telegram_id,))
            return cursor.fetchone() is not None

    def update_team_status(self, team_id: int, status: str, comment: str = None) -> bool:
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            if comment:
                cursor.execute('''
                    UPDATE teams 
                    SET status = ?, admin_comment = ?
                    WHERE id = ?
                ''', (status, comment, team_id))
            else:
                cursor.execute('''
                    UPDATE teams 
                    SET status = ?
                    WHERE id = ?
                ''', (status, team_id))
            conn.commit()
            return cursor.rowcount > 0

    def get_all_teams(self) -> List[dict]:
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT t.id, t.team_name, t.status, t.registration_date, t.captain_contact, t.admin_comment
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

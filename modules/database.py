import sqlite3
import os
import hashlib
from datetime import datetime

class Database:
    def __init__(self, db_name="quantpro.db"):
        # DB 파일 저장 경로 설정 (data 폴더 아래)
        self.db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", db_name)
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _init_db(self):
        """테이블 초기화: 유저 테이블과 유저별 찜 목록 테이블 생성"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 1. 사용자(Users) 테이블
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 2. 유저별 관심종목(Watchlist) 테이블
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_watchlist (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    ticker TEXT NOT NULL,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, ticker),
                    FOREIGN KEY(user_id) REFERENCES users(id)
                )
            ''')
            conn.commit()

    # --- [인증 (Auth) 관련 메서드] ---
    
    def _hash_password(self, password):
        """비밀번호를 SHA-256으로 암호화 (보안 처리)"""
        return hashlib.sha256(password.encode()).hexdigest()

    def create_user(self, username, password):
        """회원가입 로직"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)', 
                               (username, self._hash_password(password)))
                conn.commit()
                return True, "회원가입 성공"
            except sqlite3.IntegrityError:
                return False, "이미 존재하는 아이디입니다."

    def verify_user(self, username, password):
        """로그인 검증 로직 (성공 시 user_id 반환, 실패 시 None 반환)"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM users WHERE username = ? AND password_hash = ?', 
                           (username, self._hash_password(password)))
            result = cursor.fetchone()
            return result[0] if result else None

    # --- [Watchlist 관련 메서드 (user_id 필수 입력으로 변경)] ---

    def toggle_watchlist(self, user_id, ticker):
        """유저별 찜 목록 추가/삭제 (토글)"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # 먼저 찜해둔 상태인지 확인
            cursor.execute('SELECT 1 FROM user_watchlist WHERE user_id = ? AND ticker = ?', (user_id, ticker))
            exists = cursor.fetchone()
            
            if exists:
                cursor.execute('DELETE FROM user_watchlist WHERE user_id = ? AND ticker = ?', (user_id, ticker))
                conn.commit()
                return False # 삭제됨
            else:
                cursor.execute('INSERT INTO user_watchlist (user_id, ticker) VALUES (?, ?)', (user_id, ticker))
                conn.commit()
                return True # 추가됨

    def get_watchlist(self, user_id):
        """해당 유저의 찜 목록 전체 조회"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT ticker FROM user_watchlist WHERE user_id = ? ORDER BY added_at DESC', (user_id,))
            rows = cursor.fetchall()
            return [row[0] for row in rows]

    def is_in_watchlist(self, user_id, ticker):
        """해당 유저가 이 종목을 찜했는지 확인"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT 1 FROM user_watchlist WHERE user_id = ? AND ticker = ?', (user_id, ticker))
            return bool(cursor.fetchone())

    def remove_from_watchlist(self, user_id, ticker):
        """해당 유저의 찜 목록에서 특정 종목 강제 삭제"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM user_watchlist WHERE user_id = ? AND ticker = ?', (user_id, ticker))
            conn.commit()
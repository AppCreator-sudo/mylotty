import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, Float, String, Text, update, BigInteger, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import select
import json
from sqlalchemy import text
import string
import random
from datetime import datetime, timedelta

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    user_id = Column(BigInteger, primary_key=True)
    balance = Column(Float, default=0)
    referrals = Column(Text, default='[]')  # JSON-строка
    earned = Column(Float, default=0)
    ref_purchases = Column(Integer, default=0)
    history = Column(Text, default='[]')  # JSON-строка
    invited_by = Column(BigInteger, nullable=True)  # user_id пригласившего
    lang = Column(String, default='ru')  # язык пользователя (ru/en)
    last_sticker_id = Column(BigInteger, nullable=True)  # ID последнего стикера для удаления

class Draw(Base):
    __tablename__ = 'draws'
    id = Column(Integer, primary_key=True)
    code = Column(String(6), unique=True, index=True)  # Номер тиража
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime)
    is_active = Column(Boolean, default=True)

class DrawEntry(Base):
    __tablename__ = 'draw_entries'
    id = Column(Integer, primary_key=True)
    draw_id = Column(Integer, ForeignKey('draws.id'))
    user_id = Column(BigInteger)
    tickets = Column(Integer, default=1)

class AsyncDatabase:
    def __init__(self, dsn):
        self.engine = create_async_engine(dsn, echo=False, future=True)
        self.async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)

    async def init(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            # Проверяем, есть ли столбец last_sticker_id, если нет - добавляем
            try:
                await conn.execute(text("SELECT last_sticker_id FROM users LIMIT 1"))
            except:
                await conn.execute(text("ALTER TABLE users ADD COLUMN last_sticker_id BIGINT"))
                await conn.commit()

    async def get_user(self, user_id: int):
        print(f"[DEBUG] Ищу пользователя с user_id={user_id}")
        async with self.async_session() as session:
            result = await session.execute(select(User).where(User.user_id == user_id))
            user = result.scalar_one_or_none()
            if user:
                print(f"[DEBUG] Пользователь найден: {user_id}")
                return user
            # Если пользователя нет — создаём
            print(f"[DEBUG] Пользователь не найден, создаю: {user_id}")
            user = User(user_id=user_id)
            session.add(user)
            await session.commit()
            print(f"[DEBUG] Пользователь создан и добавлен в БД: {user_id}")
            return user

    async def update_user(self, user: User):
        async with self.async_session() as session:
            await session.merge(user)
            await session.commit()

    # Утилиты для работы с JSON-полями
    @staticmethod
    def get_referrals(user: User):
        return json.loads(user.referrals) if user.referrals else []

    @staticmethod
    def set_referrals(user: User, referrals):
        user.referrals = json.dumps(referrals)

    @staticmethod
    def get_history(user: User):
        return json.loads(user.history) if user.history else []

    @staticmethod
    def set_history(user: User, history):
        user.history = json.dumps(history)

    async def process_withdrawal(self, user_id: int, amount: float, cryptopay) -> bool:
        user = await self.get_user(user_id)
        if user.balance < amount:
            return False
        transfer_amount = amount - 0.1  # комиссия
        if transfer_amount <= 0:
            return False
        result = await cryptopay.transfer(
            user_id=user_id,
            amount=transfer_amount,
            comment="Вывод средств из лотерейного бота"
        )
        if result.get("ok"):
            user.balance -= amount
            await self.update_user(user)
            return True
        return False

    async def update_user_language(self, user_id: int, lang: str):
        async with self.async_session() as session:
            await session.execute(
                update(User).where(User.user_id == user_id).values(lang=lang)
            )
            await session.commit()

    async def get_active_draw(self):
        async with self.async_session() as session:
            now = datetime.utcnow()
            result = await session.execute(
                select(Draw).where(Draw.is_active == True, Draw.end_time > now)
            )
            draw = result.scalar_one_or_none()
            return draw

    async def create_new_draw(self, duration_minutes=10):
        async with self.async_session() as session:
            code = self._generate_draw_code()
            now = datetime.utcnow()
            end_time = now + timedelta(minutes=duration_minutes)
            draw = Draw(code=code, start_time=now, end_time=end_time, is_active=True)
            session.add(draw)
            await session.commit()
            await session.refresh(draw)
            return draw

    def _generate_draw_code(self):
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

    async def add_entry(self, draw_id, user_id, tickets=1):
        async with self.async_session() as session:
            entry = await session.execute(
                select(DrawEntry).where(DrawEntry.draw_id == draw_id, DrawEntry.user_id == user_id)
            )
            entry = entry.scalar_one_or_none()
            if entry:
                entry.tickets += tickets
            else:
                entry = DrawEntry(draw_id=draw_id, user_id=user_id, tickets=tickets)
                session.add(entry)
            await session.commit()

    async def finish_draw(self, draw: Draw):
        async with self.async_session() as session:
            draw.is_active = False
            await session.merge(draw)
            await session.commit()

    async def get_draw_entries(self, draw_id):
        async with self.async_session() as session:
            result = await session.execute(
                select(DrawEntry).where(DrawEntry.draw_id == draw_id)
            )
            return result.scalars().all()

    async def get_draw_by_code(self, code):
        async with self.async_session() as session:
            result = await session.execute(
                select(Draw).where(Draw.code == code)
            )
            return result.scalar_one_or_none()

    async def get_finished_draws(self):
        async with self.async_session() as session:
            now = datetime.utcnow()
            result = await session.execute(
                select(Draw).where(Draw.is_active == True, Draw.end_time <= now)
            )
            return result.scalars().all()

# Пример DSN: 'postgresql+asyncpg://user:password@localhost:5432/localhost' 
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, Float, String, Text, update, BigInteger
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import select
import json

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

class AsyncDatabase:
    def __init__(self, dsn):
        self.engine = create_async_engine(dsn, echo=False, future=True)
        self.async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)

    async def init(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

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

# Пример DSN: 'postgresql+asyncpg://user:password@localhost:5432/localhost' 
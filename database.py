from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from config import DEFAULT_CITY, DEFAULT_MIN_PRICE, DEFAULT_MAX_PRICE, DEFAULT_KEYWORDS

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, unique=True)
    username = Column(String)
    first_name = Column(String)
    last_name = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    
    search_city = Column(String, default=DEFAULT_CITY)
    search_min_price = Column(Integer, default=DEFAULT_MIN_PRICE)
    search_max_price = Column(Integer, default=DEFAULT_MAX_PRICE)
    search_keywords = Column(Text, default=DEFAULT_KEYWORDS)
    
    notify_enabled = Column(Boolean, default=True)
    last_notification = Column(DateTime)

class Book(Base):
    __tablename__ = 'books'
    
    id = Column(Integer, primary_key=True)
    avito_id = Column(String, unique=True)
    title = Column(String)
    price = Column(Float)
    description = Column(Text)
    url = Column(String)
    image_url = Column(String)
    city = Column(String)
    published_at = Column(DateTime)
    found_at = Column(DateTime, default=datetime.now)
    is_notified = Column(Boolean, default=False)

class Database:
    def __init__(self, db_path="books.db"):
        self.engine = create_engine(f'sqlite:///{db_path}')
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
    
    def get_session(self):
        return self.Session()
    
    def add_user(self, user_id, username=None, first_name=None, last_name=None):
        session = self.get_session()
        try:
            user = session.query(User).filter_by(user_id=user_id).first()
            if not user:
                user = User(
                    user_id=user_id,
                    username=username,
                    first_name=first_name,
                    last_name=last_name
                )
                session.add(user)
                session.commit()
            return user
        finally:
            session.close()
    
    def get_user(self, user_id):
        session = self.get_session()
        try:
            return session.query(User).filter_by(user_id=user_id).first()
        finally:
            session.close()
    
    def update_user_settings(self, user_id, **kwargs):
        session = self.get_session()
        try:
            user = session.query(User).filter_by(user_id=user_id).first()
            if user:
                for key, value in kwargs.items():
                    if hasattr(user, key):
                        setattr(user, key, value)
                session.commit()
            return user
        finally:
            session.close()
    
    def get_users(self, active_only=True):
        session = self.get_session()
        try:
            query = session.query(User)
            if active_only:
                query = query.filter_by(is_active=True)
            return query.all()
        finally:
            session.close()
    
    def save_book(self, book_data):
        session = self.get_session()
        try:
            book = session.query(Book).filter_by(avito_id=book_data['avito_id']).first()
            if not book:
                book = Book(**book_data)
                session.add(book)
                session.commit()
                return book
            return None
        finally:
            session.close()
    
    def get_new_books(self):
        session = self.get_session()
        try:
            return session.query(Book).filter_by(is_notified=False).all()
        finally:
            session.close()
    
    def mark_as_notified(self, book_ids):
        session = self.get_session()
        try:
            session.query(Book).filter(Book.id.in_(book_ids)).update(
                {"is_notified": True}, synchronize_session=False
            )
            session.commit()
        finally:
            session.close()

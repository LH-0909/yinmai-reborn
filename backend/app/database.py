import os
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import create_engine, String, Text, JSON, ForeignKey
from sqlalchemy.dialects.mysql import DATETIME
from sqlalchemy.engine import URL
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / '.env')
STORAGE = Path(os.environ.get('STORAGE_DIR', str(ROOT / 'runtime' / 'storage'))).resolve()
STORAGE.mkdir(parents=True, exist_ok=True)
url = URL.create('mysql+pymysql', username=os.getenv('MYSQL_USER', 'yinmai'),
    password=os.getenv('MYSQL_PASSWORD', ''), host=os.getenv('MYSQL_HOST', '127.0.0.1'),
    port=int(os.getenv('MYSQL_PORT', '13306')), database=os.getenv('MYSQL_DATABASE', 'yinmai'),
    query={'charset': 'utf8mb4'})
engine = create_engine(url, pool_pre_ping=True, pool_recycle=1800)
Session = sessionmaker(engine, expire_on_commit=False)

def now():
    return datetime.now(timezone.utc).replace(tzinfo=None)

class Base(DeclarativeBase):
    pass

class Seal(Base):
    __tablename__ = 'seals'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    title: Mapped[str] = mapped_column(String(150))
    filename: Mapped[str] = mapped_column(String(255))
    sha256: Mapped[str] = mapped_column(String(64))
    source_kind: Mapped[str] = mapped_column(String(32), default='user_upload')
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), default=now)
    artifacts: Mapped[list['Artifact']] = relationship(back_populates='seal', cascade='all, delete-orphan', order_by='Artifact.created_at')

class Artifact(Base):
    __tablename__ = 'artifacts'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    seal_id: Mapped[str] = mapped_column(ForeignKey('seals.id'))
    kind: Mapped[str] = mapped_column(String(32))
    filename: Mapped[str] = mapped_column(String(255))
    media_type: Mapped[str] = mapped_column(String(100))
    details: Mapped[dict] = mapped_column('metadata', JSON)
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), default=now)
    seal: Mapped[Seal] = relationship(back_populates='artifacts')

class Event(Base):
    __tablename__ = 'events'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    seal_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    action: Mapped[str] = mapped_column(String(64))
    details: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), default=now)

class Knowledge(Base):
    __tablename__ = 'knowledge'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    title: Mapped[str] = mapped_column(String(150))
    category: Mapped[str] = mapped_column(String(32))
    content: Mapped[str] = mapped_column(Text)
    source_title: Mapped[str] = mapped_column(String(255))
    source_url: Mapped[str] = mapped_column(String(500))
    image: Mapped[str] = mapped_column(String(100))

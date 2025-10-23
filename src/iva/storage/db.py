import asyncio, contextlib
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from ..config import settings

engine = None
Session = None

def init_db():
    global engine, Session
    if not settings.use_postgres or not settings.postgres_dsn:
        return
    engine = create_async_engine(settings.postgres_dsn, echo=False, future=True)
    Session = async_sessionmaker(engine, expire_on_commit=False)

@contextlib.asynccontextmanager
async def get_session():
    if not Session:
        yield None
    else:
        async with Session() as s:
            yield s

import os
import tempfile
import pytest

_dir=tempfile.TemporaryDirectory()
os.environ['DATABASE_URL']=f'sqlite:///{_dir.name}/test.db'
os.environ['ADMIN_PASSWORD']='Admin#12345!'
os.environ['SECRET_KEY']='local-only-test-secret-not-for-production-1234'
os.environ['UPLOAD_DIR']=f'{_dir.name}/uploads'

@pytest.fixture(autouse=True)
def clean_database():
    from app.db import Base, engine
    from app import models
    Base.metadata.drop_all(engine)
    yield

from app import app, db
from app.models import User, NBAStats

db.create_all()


@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'User': User, 'Post': Post}

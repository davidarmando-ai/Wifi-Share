import sqlite3
import click
from flask import g, current_app


def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(
            current_app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row
        g.db.execute('PRAGMA foreign_keys = ON')
    return g.db


def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_schema(db):
    db.executescript('''
        CREATE TABLE IF NOT EXISTS redes (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            nome        TEXT    NOT NULL,
            ssid        TEXT    NOT NULL,
            senha       TEXT    NOT NULL,
            seguranca   TEXT    NOT NULL DEFAULT 'WPA',
            descricao   TEXT,
            ativa       INTEGER NOT NULL DEFAULT 1,
            criada_em   TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
            acessos     INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS acessos (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            rede_id     INTEGER NOT NULL REFERENCES redes(id) ON DELETE CASCADE,
            ip          TEXT,
            user_agent  TEXT,
            acessado_em TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        );

        CREATE TABLE IF NOT EXISTS sessoes (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            rede_id     INTEGER NOT NULL REFERENCES redes(id) ON DELETE CASCADE,
            ip          TEXT    NOT NULL,
            iniciada_em TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
            expira_em   TEXT    NOT NULL,
            bloqueada   INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS config (
            chave   TEXT PRIMARY KEY,
            valor   TEXT
        );

        INSERT OR IGNORE INTO config (chave, valor) VALUES
            ('titulo_site', 'WiFi Share'),
            ('subtitulo',   'Partilhe a sua rede com facilidade'),
            ('tema',        'dark'),
            ('senha_admin', 'admin123'),
            ('limite_minutos', '30');
    ''')
    db.commit()


def init_db(app):
    app.teardown_appcontext(close_db)

    import os
    os.makedirs(os.path.dirname(app.config['DATABASE']), exist_ok=True)

    with app.app_context():
        db = get_db()
        init_schema(db)

    @app.cli.command('init-db')
    def init_db_command():
        with app.app_context():
            init_schema(get_db())
        click.echo('Base de dados iniciada.')

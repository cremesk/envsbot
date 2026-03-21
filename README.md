# envsbot

A modular XMPP bot built with Python 3 and slixmpp.

> ⚠️ **Early Stage Warning**
> This project is still in active development. Features may change, break, or be incomplete.

---

## 🌐 envs pubnix/tilde

envsbot is developed with the **envs pubnix** environment in mind, but is not limited to it.

---

## 📖 About

envsbot is a lightweight, plugin-driven XMPP bot designed for flexibility and experimentation.

---

## ✨ Features

* Plugin-based architecture
* Dynamic plugin loading / reloading
* Command system via decorators
* Structured database layer (in progress)
* Test suite for core systems and plugins

---

## 📁 Project Structure

```id="1ly8zn"
envsbot/
├── envsbot.py         # Main bot entrypoint
├── plugins/           # Plugin modules
├── utils/             # Core systems (commands, plugin manager)
├── database/          # Database layer (WIP)
├── tests/             # Test suite
├── requirements.txt
└── README.md
```

---

## ⚙️ Installation

```bash id="06szmh"
git clone https://github.com/yourusername/envsbot.git
cd envsbot
python -m venv venv
source venv/bin/activate  # Linux/macOS
pip install -r requirements.txt
```

---

## ▶️ Running the Bot

```bash id="hw0mgg"
python envsbot.py
```

---

## 🧩 Plugins (Quick Overview)

Plugins live in the `plugins/` directory and extend the bot’s functionality.

They can:

* Register commands
* Hook into bot events
* Be dynamically loaded or reloaded at runtime

Example plugins include:

* `help.py`
* `status.py`
* `rooms.py`
* `users.py`

---

## 💬 Commands

Commands are defined using decorators in the command system.

Plugins can register commands that users trigger via chat messages.

*(More detailed documentation coming later.)*

---

## 🧪 Testing

Run tests with:

```bash id="zqopwb"
pytest
```

The project includes tests for:

* Command system
* Plugin loading and isolation
* Core functionality

---

## 🛠️ Development Status

This project is under active development. Current areas in progress:

* Database layer completion
* Plugin dependency handling improvements
* Additional core plugins

---

## 📄 License

MIT License

---

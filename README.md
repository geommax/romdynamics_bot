# romdynamics_bot

## 0) Project folder သို့ဝင်ပါ

```bash
cd chat
```

`bot.py`, `requirements.txt` တွေရှိနေကြောင်းစစ်ပါ။

```bash
ls -la
```

## 1) System packages install on brew (Python, ffmpeg)

```bash
sudo apt update
sudo apt install -y python
```

## 2) Python virtual environment တည်ဆောက်ပါ

project folder ထဲမှာ venv ဖန်တီးပါ:

```bash
python3 -m venv venv
```

## 3) Python dependencies install

```bash
pip install python-telegram-bot
```

## 4) Telegram Bot Token ပြင်ဆင်ပါ


```bash
source venv/bin/activate
export TELEGRAM_BOT_TOKEN="YOUR_BOT_TOKEN"
export AUTHORIZED_USERNAME="YOUR_AUTHORIZED_NAME"
```

## 5) Bot run လုပ်ပါ

```bash
python bot.py
```

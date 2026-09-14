# Налаштування на Linux

Українська · [Русский](../ru/setup-linux.md) · [English](../en/setup-linux.md)

Одноразове встановлення та налаштування інструментів на системі Linux (Ubuntu, Debian та інших дистрибутивах).

## 1. Встановлення Python, FFmpeg та Git

На Ubuntu або Debian виконайте:

```sh
sudo apt update && sudo apt install -y python3 ffmpeg git
```

*(У Fedora використовуйте `sudo dnf install -y python3 ffmpeg git`; в Arch Linux — `sudo pacman -Syu python ffmpeg git`)*.

## 2. Клонування репозиторію

Клонуйте репозиторій на ваш комп'ютер або сервер:

```sh
git clone https://github.com/before-we-build/agentic-evangelism.git
cd agentic-evangelism
```

## 3. Перевірка готовності середовища

Запустіть утиліту самодіагностики:

```sh
python3 skills/suno-tiktok-video/scripts/doctor.py
```

**Ви маєте побачити:** `Overall Ready: YES`.

Наступний крок: [Створення першого відео](first-video.md).

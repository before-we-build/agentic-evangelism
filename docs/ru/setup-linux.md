# Настройка на Linux

[Українська](../uk/setup-linux.md) · Русский · [English](../en/setup-linux.md)

Однократная установка и настройка инструментов на системе Linux (Ubuntu, Debian и других дистрибутивах).

## 1. Установка Python, FFmpeg и Git

На Ubuntu или Debian выполните:

```sh
sudo apt update && sudo apt install -y python3 ffmpeg git
```

*(В Fedora используйте `sudo dnf install -y python3 ffmpeg git`; в Arch Linux — `sudo pacman -Syu python ffmpeg git`)*.

## 2. Клонирование репозитория

Клонируйте репозиторий на ваш компьютер или сервер:

```sh
git clone https://github.com/before-we-build/agentic-evangelism.git
cd agentic-evangelism
```

## 3. Проверка готовности окружения

Запустите утилиту самодиагностики:

```sh
python3 skills/suno-tiktok-video/scripts/doctor.py
```

**Вы должны увидеть:** `Overall Ready: YES`.

Следующий шаг: [Создание первого видео](first-video.md).

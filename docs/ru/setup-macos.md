# Настройка на macOS

[Українська](../uk/setup-macos.md) · Русский · [English](../en/setup-macos.md)

Однократная установка и настройка инструментов на компьютере Mac.

## 1. Установка Python, FFmpeg и Git

Откройте Terminal и установите Python, FFmpeg и Git с помощью [Homebrew](https://brew.sh):

```sh
brew install python ffmpeg git
```

## 2. Клонирование репозитория

Клонируйте репозиторий на ваш компьютер:

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

# Налаштування на macOS

Українська · [Русский](../ru/setup-macos.md) · [English](../en/setup-macos.md)

Одноразове встановлення та налаштування інструментів на комп'ютері Mac.

## 1. Встановлення Python, FFmpeg та Git

Відкрийте Terminal і встановіть Python, FFmpeg та Git за допомогою [Homebrew](https://brew.sh):

```sh
brew install python ffmpeg git
```

## 2. Клонування репозиторію

Клонуйте репозиторій на ваш комп'ютер:

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

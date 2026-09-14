# Налаштування на Windows

Українська · [Русский](../ru/setup-windows.md) · [English](../en/setup-windows.md)

Одноразове встановлення та налаштування інструментів на комп'ютері з Windows.

## 1. Встановлення Python та FFmpeg

Відкрийте PowerShell або командний рядок (Термінал) і встановіть Python та FFmpeg за допомогою `winget`:

```sh
winget install Python.Python.3.12
```

```sh
winget install Gyan.FFmpeg
```

Після завершення встановлення перезапустіть вікно терміналу, щоб оновилася змінна `PATH`.

## 2. Клонування репозиторію

Завантажте репозиторій зі скілами:

```sh
git clone https://github.com/before-we-build/agentic-evangelism.git
cd agentic-evangelism
```

## 3. Перевірка готовності середовища

Запустіть утиліту самодіагностики, щоб переконатися, що Python, FFmpeg та потрібні кодеки знайдені:

```sh
python skills/suno-tiktok-video/scripts/doctor.py
```

**Ви маєте побачити:** `Overall Ready: YES`.

Наступний крок: [Створення першого відео](first-video.md).

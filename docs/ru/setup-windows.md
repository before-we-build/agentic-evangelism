# Настройка на Windows

[Українська](../uk/setup-windows.md) · Русский · [English](../en/setup-windows.md)

Однократная установка и настройка инструментов на компьютере с Windows.

## 1. Установка Python и FFmpeg

Откройте PowerShell или командную строку (Терминал) и установите Python и FFmpeg с помощью `winget`:

```sh
winget install Python.Python.3.12
```

```sh
winget install Gyan.FFmpeg
```

После завершения установки перезапустите окно терминала, чтобы обновилась переменная `PATH`.

## 2. Клонирование репозитория

Скачайте репозиторий со скиллами:

```sh
git clone https://github.com/before-we-build/agentic-evangelism.git
cd agentic-evangelism
```

## 3. Проверка готовности окружения

Запустите утилиту самодиагностики, чтобы убедиться, что Python, FFmpeg и нужные кодеки найдены:

```sh
python skills/suno-tiktok-video/scripts/doctor.py
```

**Вы должны увидеть:** `Overall Ready: YES`.

Следующий шаг: [Создание первого видео](first-video.md).

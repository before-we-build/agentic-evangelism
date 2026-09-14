# Подготовка и проверка видео на macOS

[English](macos.md) · [Русский](macos.ru.md) · [Українська](macos.uk.md)

На macOS команды выполняются в Terminal (zsh или bash).

## Загрузки и расположение файлов

По умолчанию исходная аудиозапись ищется в папке «Загрузки» пользователя:
- Путь: `~/Downloads` (например, `/Users/username/Downloads`).
- Автоматически определяется через `platform_utils.py`.

## Инструменты и зависимости

Установите Python 3 и FFmpeg через [Homebrew](https://brew.sh):

```sh
brew install python ffmpeg
```

Проверьте готовность инструментов и кодеков:

```sh
python3 scripts/doctor.py
```

## Запуск пайплайна

Сборка видео из аудиозаписи и раскадровки:

```sh
python3 scripts/build_video.py --audio "$HOME/Downloads/song.mp3" --storyboard "/absolute/workspace/storyboard.json" --output "$HOME/Downloads/TikTok_song.mp4"
```

## Доступность и ручная публикация

Готовый MP4-файл сохраняется в вашу папку «Загрузки»:
- Проверьте видео в QuickTime Player или через пробел в Finder.
- Скилл никогда не публикует видео автоматически.
- Для публикации откройте [tiktok.com/upload](https://www.tiktok.com/upload) в Safari или Chrome, выберите проверенный MP4 из папки «Загрузки» и опубликуйте вручную.

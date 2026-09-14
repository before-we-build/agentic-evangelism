# Підготовка та перевірка відео на macOS

[English](macos.md) · [Русский](macos.ru.md) · [Українська](macos.uk.md)

На macOS команди виконуються в Terminal (zsh або bash).

## Завантаження та розташування файлів

За замовчуванням вихідний аудіозапис шукається в папці «Завантаження» користувача:
- Шлях: `~/Downloads` (наприклад, `/Users/username/Downloads`).
- Автоматично визначається через `platform_utils.py`.

## Інструменти та залежності

Встановіть Python 3 та FFmpeg через [Homebrew](https://brew.sh):

```sh
brew install python ffmpeg
```

Перевірте готовність інструментів і кодеків:

```sh
python3 scripts/doctor.py
```

## Запуск пайплайну

Збирання відео з аудіозапису та розкадровки:

```sh
python3 scripts/build_video.py --audio "$HOME/Downloads/song.mp3" --storyboard "/absolute/workspace/storyboard.json" --output "$HOME/Downloads/TikTok_song.mp4"
```

## Доступність і ручна публікація

Готовий MP4-файл зберігається у вашу папку «Завантаження»:
- Перевірте відео у QuickTime Player або за допомогою пробілу у Finder.
- Скіл ніколи не публікує відео автоматично.
- Для публікації відкрийте [tiktok.com/upload](https://www.tiktok.com/upload) у Safari або Chrome, виберіть перевірений MP4 із Завантажень і опублікуйте вручну.

# Підготовка та перевірка відео на Linux

[English](linux.md) · [Русский](linux.ru.md) · [Українська](linux.uk.md)

На Linux (десктоп, робоча станція або сервер) команди виконуються в Bash або Zsh.

## Завантаження та розташування файлів

За замовчуванням вихідний аудіозапис шукається в папці «Завантаження» користувача:
- Визначається через `xdg-user-dir DOWNLOAD` або стандартний шлях `~/Downloads`.
- Автоматично знаходиться через `platform_utils.py`.
- На серверах без папки Завантажень передавайте явні шляхи `--audio` та `--output`.

## Інструменти та залежності

Встановіть Python 3 та FFmpeg через пакетний менеджер вашого дистрибутива:

- **Ubuntu / Debian:**
  ```sh
  sudo apt update && sudo apt install -y python3 ffmpeg
  ```
- **Fedora:**
  ```sh
  sudo dnf install -y python3 ffmpeg
  ```
  *(Примітка: на Fedora переконайтеся, що пакет містить повні кодеки `libx264` та `aac`, а не обмежений `ffmpeg-free`).*
- **Arch Linux:**
  ```sh
  sudo pacman -Syu python ffmpeg
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

Готовий MP4-файл зберігається за вказаним вихідним шляхом:
- На десктопі Linux: відкрийте браузер і перейдіть на [tiktok.com/upload](https://www.tiktok.com/upload) для ручного завантаження.
- На віддаленому сервері: скопіюйте перевірений MP4 на свій комп'ютер чи телефон через `scp`, SFTP або інший зручний спосіб.
- Скіл ніколи не публікує відео автоматично.

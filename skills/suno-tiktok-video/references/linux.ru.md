# Подготовка и проверка видео на Linux

[English](linux.md) · [Русский](linux.ru.md) · [Українська](linux.uk.md)

На Linux (десктоп, рабочая станция или сервер) команды выполняются в Bash или Zsh.

## Загрузки и расположение файлов

По умолчанию исходная аудиозапись ищется в папке «Загрузки» пользователя:
- Определяется через `xdg-user-dir DOWNLOAD` или стандартный путь `~/Downloads`.
- Автоматически находится через `platform_utils.py`.
- На серверах без папки Загрузок передавайте явные пути `--audio` и `--output`.

## Инструменты и зависимости

Установите Python 3 и FFmpeg через пакетный менеджер вашего дистрибутива:

- **Ubuntu / Debian:**
  ```sh
  sudo apt update && sudo apt install -y python3 ffmpeg
  ```
- **Fedora:**
  ```sh
  sudo dnf install -y python3 ffmpeg
  ```
  *(Примечание: на Fedora убедитесь, что пакет содержит полные кодеки `libx264` и `aac`, а не урезанный `ffmpeg-free`).*
- **Arch Linux:**
  ```sh
  sudo pacman -Syu python ffmpeg
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

Готовый MP4-файл сохраняется по указанному выходному пути:
- На десктопе Linux: откройте браузер и перейдите на [tiktok.com/upload](https://www.tiktok.com/upload) для ручной загрузки.
- На удаленном сервере: скопируйте проверенный MP4 на свой компьютер или телефон через `scp`, SFTP или другой удобный способ.
- Скилл никогда не публикует видео автоматически.

# Настройка GitHub Pages для WHOOP callback

## Быстрая настройка (2 минуты)

1. **Включите GitHub Pages:**
   - Откройте репозиторий: https://github.com/FUYOH666/RAS-TGbot
   - Перейдите в Settings → Pages
   - В разделе "Source" выберите: **Deploy from a branch**
   - Branch: **main**
   - Folder: **/docs**
   - Нажмите Save

2. **Подождите 1-2 минуты** пока GitHub Pages активируется

3. **Обновите Redirect URL в WHOOP Developer Platform:**
   - Откройте настройки вашего приложения в WHOOP Developer Platform
   - Измените Redirect URL на: `https://fuyoh666.github.io/RAS-TGbot/whoop-callback.html`
   - Сохраните изменения

4. **Готово!** Теперь можно тестировать подключение через `/whoop_connect`

## Проверка

После настройки GitHub Pages страница будет доступна по адресу:
```
https://fuyoh666.github.io/RAS-TGbot/whoop-callback.html
```

Проверьте, что страница открывается в браузере.

## Как это работает

1. Пользователь авторизуется в WHOOP
2. WHOOP редиректит на GitHub Pages страницу с authorization code
3. Страница показывает code пользователю
4. Пользователь копирует code и отправляет боту `/whoop_code <code>`

**Преимущества:**
- ✅ Не требует настройки вашего сайта
- ✅ Бесплатно
- ✅ Работает сразу после включения GitHub Pages
- ✅ Автоматически обновляется при push в репозиторий


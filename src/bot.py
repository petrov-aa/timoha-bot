import os

import telebot

from aiohttp import web
from app.bot import bot


if __name__ == "__main__":

    if os.environ['APP_RUN_METHOD'] == 'pooling':

        bot.remove_webhook()
        bot.polling(none_stop=True, timeout=9999)

    elif os.environ['APP_RUN_METHOD'] == 'webhook':

        app = web.Application()

        async def handle(request):
            if request.match_info.get('token') == bot.token:
                request_body_dict = await request.json()
                update = telebot.types.Update.de_json(request_body_dict)
                bot.process_new_updates([update])
                return web.Response()
            else:
                return web.Response(status=403)

        app.router.add_post('/{token}/', handle)

        web.run_app(
            app,
            host="0.0.0.0",
            port=443
        )

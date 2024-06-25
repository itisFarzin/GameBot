import inspect
import logging
import betbot
import pyrogram
import pyrogram.dispatcher


class Dispatcher(pyrogram.dispatcher.Dispatcher):

	def __init__(self, client: "betbot.BetBot"):
		super().__init__(client)

	async def handler_worker(self, lock):
		while True:
			packet = await self.updates_queue.get()

			if packet is None:
				break

			try:
				update, users, chats = packet
				parser = self.update_parsers.get(type(update), None)

				parsed_update, handler_type = (
					await parser(update, users, chats)
					if parser is not None
					else (None, type(None))
				)

				async with lock:
					for group in self.groups.values():
						for handler in group:
							args = None

							if isinstance(handler, handler_type):
								try:
									if await handler.check(self.client, parsed_update):
										args = (parsed_update,)
								except Exception as e:
									logging.exception(e)
									continue

							elif isinstance(handler, pyrogram.handlers.RawUpdateHandler):
								args = (update, users, chats)

							if args is None:
								continue

							try:
								new_args = []
								for arg in args:
									if isinstance(arg, pyrogram.types.Message):
										arg.__class__ = betbot.types.Message
										if arg.reply_to_message:
											arg.reply_to_message.__class__ = betbot.types.Message
									elif isinstance(arg, pyrogram.types.CallbackQuery):
										arg.__class__ = betbot.types.CallbackQuery
									new_args.append(arg)
								if inspect.iscoroutinefunction(handler.callback):
									await handler.callback(self.client, *new_args)
								else:
									if handler.callback.__code__.co_argcount == 1:
										await self.loop.run_in_executor(
											self.client.executor,
											handler.callback,
											*new_args
										)
									else:
										await self.loop.run_in_executor(
											self.client.executor,
											handler.callback,
											self.client,
											*new_args
										)
							except pyrogram.StopPropagation:
								raise
							except pyrogram.ContinuePropagation:
								continue
							except Exception as e:
								logging.exception(e)

							break
			except pyrogram.StopPropagation:
				pass
			except Exception as e:
				logging.exception(e)

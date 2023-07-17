from datetime import datetime

from aiohttp import ClientSession
from disnake import (
	ApplicationCommandInteraction,
	Embed,
	Member,
	Message,
	Role,
	TextChannel,
)
from disnake.ext.commands import Cog, slash_command
from disnake.utils import format_dt
from loguru import logger

from ...bot import Bot
from ...constants import Channels, Colors, Roles

BASE_URL = "https://osf-database-api.shuttleapp.rs"
DEV_BASE_URL = "http://127.0.0.1:8000"

class OSFValidation(Cog):
	"""Check if user is OSF member on joining."""

	def __init__(self, bot: Bot) -> None:
		self.bot = bot
		self.log_channel: TextChannel | None = None
		self.osf_member: Role | None = None
		super().__init__()
	
	async def post_message(
        self,
        embed: Embed,
    ) -> Message | None:
		"""Send the given message in the log channel."""
		if self.log_channel is None:
			await self.bot.wait_until_ready()
			self.log_channel = await self.bot.fetch_channel(Channels.log)

			if self.log_channel is None:
				logger.error(f"Failed to get log channel with ID ({Channels.log})")
		
		return await self.log_channel.send(embed=embed)

	async def process_member_status(self, member: Member) -> None:
		"""Give the OSF Member role to validated user."""
		if self.osf_member is None:
			await self.bot.wait_until_ready()
			self.osf_member = member.guild.get_role(Roles.osf_member)

			if self.osf_member is None:
				logger.error(f"Failed to get OSF Member role with ID ({Roles.osf_member})")
		
		await member.add_roles(self.osf_member)

	async def validate_member_status(self, id: int) -> bool | str:
		async with self.bot.http_session.get(
			f"{DEV_BASE_URL}/api/v1/bot/validate", 
			json={
				"id": id,
			},
		) as resp:
			if resp.status == 200:
				data = await resp.json()
				return data["result"]
			else:
				text = await resp.text()
				return f"{resp.status}: {text}"
	
	@Cog.listener()
	async def on_member_join(self, member: Member) -> None:
		"""Validates user on joining the server."""
		status = await self.validate_member_status(member.id)

		if status and isinstance(status, bool):
			await self.process_member_status(member)
			await self.post_message(
				Embed(
					title=f"OSF Member Added ({member.id})",
					description=f"{member.mention} **({member.name}) ({member.id})** was validated by the bot.",
					timestamp=datetime.now(),
					color=Colors.green,
				)
			)
		elif isinstance(status, str):
			await self.post_message(
				Embed(
					title=f"OSF Validation Failed ({member.id})",
					description=f"```{status}```",
					timestamp=datetime.now(),
					color=Colors.red,
				)
			)
	
	@slash_command()
	async def validate(self, itr: ApplicationCommandInteraction, member: Member = None) -> None:
		"""Command to validate users already in the server."""
		if not member:
			member = itr.user

def setup(bot: Bot) -> None:
	"""Loads the OSFValidation cog."""
	bot.add_cog(OSFValidation(bot))
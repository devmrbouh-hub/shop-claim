class ShopClaimChatHandler
{
	static bool HandleCommand(PlayerBase player, string text)
	{
		if (!player)
			return false;

		if (!text || text == "")
			return false;

		text = ShopClaimJsonHelper.TrimString(text);
		if (text == "")
			return false;

		ShopClaimModConfig cfg = ShopClaimSettings.Get();
		if (!cfg || !cfg.IsValid())
			return false;

		if (!cfg.enable_chat_commands)
			return false;

		string command = cfg.claim_command;
		if (command == "")
			command = "shop";

		if (!MatchesCommandPrefix(text, command))
			return false;

		string prefix = "/" + command;
		if (text.IndexOf("/wargm") == 0)
			prefix = "/wargm";

		string tail = text.Substring(prefix.Length(), text.Length() - prefix.Length());
		tail = ShopClaimJsonHelper.TrimString(tail);

		if (tail == "")
		{
			ShopClaimHttpClient.Get().RequestPendingList(player);
			return true;
		}

		if (tail == "respawn" || tail == "пересоздать")
		{
			ShopClaimService.Get().RespawnContainer(player, ShopClaimNotifyChannel.CHAT);
			return true;
		}

		if (tail == "cancel" || tail == "отмена")
		{
			ShopClaimPlayerMessenger.Send(player, "Команда отмены отключена. Используйте /" + command + " respawn или кнопку в меню магазина.");
			return true;
		}

		int index = tail.ToInt();
		if (index < 1)
		{
			ShopClaimPlayerMessenger.Send(player, cfg.messages.invalid_index);
			return true;
		}

		ShopClaimHttpClient.Get().RequestClaimByIndex(player, index);
		return true;
	}

	protected static bool MatchesCommandPrefix(string text, string command)
	{
		if (text.IndexOf("/" + command) == 0)
			return true;
		if (command == "shop" && text.IndexOf("/wargm") == 0)
			return true;
		return false;
	}

	static bool TryHandle(ChatMessageEventParams params)
	{
		if (!params)
			return false;

		string senderName = params.param2;
		string text = params.param3;

		PlayerBase player = FindPlayerByName(senderName);
		if (!player)
			return false;

		return HandleCommand(player, text);
	}

	protected static PlayerBase FindPlayerByName(string name)
	{
		array<Man> players = new array<Man>();
		GetGame().GetPlayers(players);

		foreach (Man man : players)
		{
			PlayerBase player = PlayerBase.Cast(man);
			if (!player || !player.GetIdentity())
				continue;

			if (player.GetIdentity().GetName() == name)
				return player;
		}

		return null;
	}
};
